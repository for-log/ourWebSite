from flask import Flask, render_template, url_for, request
from flask_socketio import SocketIO, join_room, leave_room, emit
from mysql.connector import connect, Error
from random import randrange, choice

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ForMilfABC'
socket = SocketIO(app)
auths = {}
ingame = {}
games = {}

class Game:
    def __init__(self, idx, user):
        self.idx = idx
        self.users = [auths[user][0]]
        self.field = [[0 for j in range(3)] for i in range(3)]
        self.step = 0
        self.laststep = 0

    def __repr__(self):
        text = f"<div class='game' onclick='connect(this)' id='{self.idx}'>{self.users[0]}</div>"
        return text

    @property
    def len(self):
        return len(self.users)

    def add(self, user):
        if len(self.users) < 2:
            self.users.append(auths[user][0])
            self.laststep = auths[user][0]
            return 1
        else:
            return 0

    def remove(self, user):
        self.users.remove(auths[user][0])
        try:
            return self.users[0]
        except Exception:
            del self

    def who_win(self):
        isDraw = 0
        for i in range(len(self.field)):
            if (self.field[i][0], self.field[i][1], self.field[i][2]) in ((1,1,1), (2,2,2)):
                return self.field[i][0]
            if (self.field[i][0], self.field[i][1], self.field[i][2]).count(0) == 0:
                isDraw+=1
        for i in range(len(self.field)):
            if (self.field[0][i], self.field[1][i], self.field[2][i]) in ((1,1,1), (2,2,2)):
                return self.field[0][i]
        if (self.field[0][2], self.field[1][1], self.field[2][0]) in ((1,1,1), (2,2,2)):
            return self.field[0][2]
        if (self.field[0][0], self.field[1][1], self.field[2][2]) in ((1,1,1), (2,2,2)):
            return self.field[0][0]
        if isDraw == 3:
            return 3
        return -1


    def set_field(self, pos, user):
        if auths[user][0] == self.laststep:
            return 0, 0
        if self.field[pos[0]][pos[1]] == 0:
            self.field[pos[0]][pos[1]] = 1 if self.step%2 == 0 else 2
            self.step += 1
            self.laststep = auths[user][0]
            return 1, self.field[pos[0]][pos[1]]
        else:
            return 0, 0


class Connection:
    def __init__(self, host, user, password, db):
        try:
            self.conn = connect(host=host, user=user,password=password)
            with self.conn.cursor() as c:
                c.execute(f"USE {db};")
        except Error as e:
            raise Exception("Connection error!")

    def execute(self, req):
        result = []
        with self.conn.cursor() as cursor:
            cursor.execute(req)
            for db in cursor:
                result.append(db)
        return result

    def change_execute(self, req):
        with self.conn.cursor() as cursor:
            cursor.execute(req)
            self.conn.commit()

def SUCCESS(data):
    return {'type':"success", "data":data}
def FAIL(data):
    return {'type':"error", "data":data}

conn = Connection("localhost", "root", "f0rder_Hello", "users")

@app.route("/")
def page():
    return render_template("page.html")

@app.route("/raw-page-main")
def main_page():
    return render_template("main.html")

@app.route("/raw-page-about")
def about_page():
    return render_template("about.html")

@app.route("/raw-page-register")
def register_page():
    return render_template("register_form.html")

@socket.on("/raw-register-request")
def register_request_page(data):
    name_user = data['name']
    password_user = data['password']
    size = conn.execute(f"SELECT * FROM users where name = '{name_user}'")
    if len(size) > 0:
        return FAIL('')
    conn.change_execute(f"INSERT INTO users (name, password) VALUES ('{name_user}', '{password_user}')")
    auths[request.sid] = (name_user, password_user)
    return SUCCESS(render_template("logout.html"))

@app.route("/raw-page-login")
def login_page():
    return render_template("login_form.html")

@socket.on("/raw-login-request")
def login_request_page(data):
    name_user = data["name"]
    password_user = data["password"]
    size = conn.execute(f"SELECT * FROM users where name = '{name_user}' and password = '{password_user}'")
    if len(size) > 0:
        auths[request.sid] = (name_user, password_user)
        return SUCCESS(render_template("logout.html"))
    else:
        return FAIL(render_template("auth.html"))

@socket.on("/raw-logout-request")
def logout_request_page(data):
    del auths[request.sid]
    return SUCCESS(render_template("auth.html"))

@socket.on("/allgames")
def get_games(data):
    result = ""
    for game in games:
        if games[game].len == 0:
            socket.emit("/delete-room", {"id":games[game].idx})
            del games[game]
        if games[game]:
            result += repr(games[game])
    if len(games) > 0:
        return SUCCESS(result)
    else:
        return FAIL("NO")

@socket.on("/game")
def join_game(data):
    if auths.get(request.sid) == None:
        return FAIL("Error in join")
    if data["type"] == "random":
        if len(games) < 1:
            idx = randrange(0, 100000)
            game = Game(idx, request.sid)
            games.update({idx:game});
            join_room(str(idx))
            ingame.update({request.sid:game})
            return SUCCESS(render_template("field.html"))
        else:
            while 1:
                idx, game = choice(list(games.items()))
                if game.add(request.sid):
                    join_room(str(idx))
                    ingame.update({request.sid: game});
                    return SUCCESS(render_template("field.html"))
    else:
        game = games.get(int(data["idx"]))
        if game != None:
            if (game.add(request.sid)):
                join_room(str(data["idx"]))
                ingame.update({request.sid:game})
                return SUCCESS(render_template("field.html"))
            else:
                return FAIL(render_template("fail_join.html"))
        else:
            game = Game(int(data["idx"]), request.sid)
            games.update({game.idx:game})
            join_room(str(data["idx"]))
            ingame.update({request.sid:game})
            return SUCCESS(render_template("field.html"))

@socket.on("/make-step")
def make_step(data):
    pos = list(map(int, data['id']))
    game = ingame[request.sid]
    status = game.set_field(pos, request.sid)
    isEnd = game.who_win()
    if (status[0]):
        emit("/was-step", {"x":pos[0], "y":pos[1], "step":status[1]}, to=str(ingame[request.sid].idx))
    if (isEnd != -1):
        emit("/select-winner", {'winner':game.users[isEnd-1]}, to=str(ingame[request.sid].idx))
        if isEnd != 3:
            conn.change_execute(f"UPDATE users SET points = 100 WHERE name = '{game.users[isEnd-1]}';")
        else:
            for user in game.users:
                conn.change_execute(f"UPDATE users SET points = 100 WHERE name = '{user}';")
        del ingame[request.sid]
        del games[game.idx]

@socket.on("/leave-room")
def leave_room():
    game = ingame.get(request.sid)
    if game != None:
        winner = game.remove(request.sid)
        emit("/select-winner", {'winner':winner}, to=str(ingame[request.sid].idx))
        del ingame[request.sid]

@socket.on("/close-window")
def remove_user():
    game = ingame.get(request.sid)
    auth = auths.get(request.sid)
    if game != None:
        winner = game.remove(request.sid)
        emit("/select-winner", {'winner':winner}, to=str(ingame[request.sid].idx))
        del ingame[request.sid]
    if auth:
        del auths[request.sid]

if __name__ == "__main__":
    socket.run(app, debug=True)
