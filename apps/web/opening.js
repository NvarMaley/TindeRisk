/* V2 opening animation, with the original waterline, reflection and title CSS. */
(() => {
  const scene=document.getElementById("opening");
  const start=document.getElementById("intro-start");
  const loading=document.getElementById("intro-loading");
  const loadingDuration=5000;
  let finished=false, timer;
  function enterStudio(){
    if(finished)return;
    finished=true;clearTimeout(timer);
    document.removeEventListener("keydown",startFromKeyboard);
    scene.hidden=true;
    document.body.removeAttribute("data-opening");
    page("saves");
    document.getElementById("save-slot").focus();
  }
  function begin(){
    if(scene.dataset.phase!=="idle")return;
    scene.dataset.phase="rising";start.disabled=true;loading.hidden=false;
    document.dispatchEvent(new Event("riskmatch:intro-start"));
    timer=setTimeout(enterStudio,loadingDuration);
  }
  function startFromKeyboard(event){
    if(event.key!=="Enter"||event.repeat||event.altKey||event.ctrlKey||event.metaKey)return;
    if(event.target?.closest?.("button,select,input,a"))return;
    if(scene.dataset.phase!=="idle")return;
    event.preventDefault();begin();
  }
  start.addEventListener("click",begin);
  document.addEventListener("keydown",startFromKeyboard);
})();
