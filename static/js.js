let mainlink = $(".link-to-main");
let aboutlink = $(".link-to-about");
let content = $(".content");

mainlink.on("click", ()=>{
  $.ajax({
    type:"GET",
    url:"/raw-page-main",
    dataType: "html",
    success: updateContent
  })
});

aboutlink.on("click", ()=>{
  $.ajax({
    type:"GET",
    url:"/raw-page-about",
    dataType: "html",
    success: updateContent
  })
});

socket.on("/delete-room", (data)=>{
  $("#" + data.id).remove();
})

function updateContent(page) {
  content.html(page);
}

function updateHeader(page){
  $(".auth_links").html(page);
}

window.onbeforeunload = (e)=>{
  socket.emit("/close-window");
}
