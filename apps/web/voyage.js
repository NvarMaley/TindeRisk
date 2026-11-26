// Decorative currents respond to the pointer; only a visible scene uses frames.
(() => {
  const reduced=matchMedia("(prefers-reduced-motion: reduce)");
  const scenes=new Map();
  let frame=0;
  function paint(canvas,s,time){
    const ctx=canvas.getContext("2d");
    if(!ctx)return;
    const w=canvas.clientWidth,h=canvas.clientHeight;
    if(!w||!h)return;
    const ratio=Math.min(devicePixelRatio||1,1.5);
    if(canvas.width!==Math.round(w*ratio)||canvas.height!==Math.round(h*ratio)){
      canvas.width=Math.round(w*ratio);canvas.height=Math.round(h*ratio);
    }
    ctx.setTransform(ratio,0,0,ratio,0,0);ctx.clearRect(0,0,w,h);
    const phase=time*.00035;
    for(let row=0;row<33;row++){
      const depth=row/32;
      ctx.beginPath();
      for(let x=-3;x<=w+5;x+=6){
        const f=x/w;
        const y=h*(.58+depth*.36+.045*Math.sin(f*7+depth*5+phase)+
          .045*Math.sin(f*3-depth*4-phase*.55)+.035*Math.cos(f*12+s.x*2)*depth);
        if(x===-3)ctx.moveTo(x,y);else ctx.lineTo(x,y);
      }
      ctx.strokeStyle=row%5===0?"rgba(255,188,195,.56)":"rgba(153,239,222,"+(.17+depth*.34)+")";
      ctx.lineWidth=.65+depth*.65;ctx.stroke();
    }
  }
  function loop(time){
    frame=0;
    if(document.hidden)return;
    let visible=false;
    for(const [canvas,s] of scenes)if(s.visible){paint(canvas,s,reduced.matches?0:time);visible=true;}
    if(visible&&!reduced.matches)frame=requestAnimationFrame(loop);
  }
  function wake(){if(!frame)frame=requestAnimationFrame(loop);}
  const observer=new IntersectionObserver(entries=>{
    for(const entry of entries)scenes.get(entry.target).visible=entry.isIntersecting;
    wake();
  });
  for(const canvas of document.querySelectorAll(".tide-canvas")){
    const state={visible:false,x:.5};scenes.set(canvas,state);observer.observe(canvas);
    canvas.parentElement.addEventListener("pointermove",e=>{
      const r=canvas.getBoundingClientRect();state.x=(e.clientX-r.left)/Math.max(1,r.width);
    });
  }
  reduced.addEventListener("change",wake);document.addEventListener("visibilitychange",wake);
  window.addEventListener("resize",wake);
})();

document.addEventListener("pointerdown",event=>{
  if(!event.isPrimary||event.button!==0||document.body.dataset.opening==="true"||
    matchMedia("(prefers-reduced-motion: reduce)").matches||
    event.target.closest("input,select,textarea,dialog"))return;
  const ring=document.createElement("i");
  ring.className="water-touch";ring.setAttribute("aria-hidden","true");
  ring.style.left=event.clientX+"px";ring.style.top=event.clientY+"px";
  document.body.append(ring);
  setTimeout(()=>ring.remove(),850);
},{passive:true});

// The home example illustrates budget arithmetic independently of a saved mandate.
(() => {
  const slider=document.getElementById("home-share");
  const answers=document.querySelectorAll("[data-guide-choice]");
  let chosen=null;
  for(const button of answers)button.addEventListener("click",()=>{
    chosen=button.dataset.guideChoice;
    for(const other of answers)other.setAttribute("aria-pressed",String(other===button));
    update();
  });
  function update(){
    if(chosen)document.getElementById("guide-reaction").textContent=window.RM.t(chosen==="steady"?"guideSteady":"guideVariableResult");
    const share=Number(slider.value);
    const fmt=new Intl.NumberFormat(window.RM.language==="fr"?"fr-CH":"en-US");
    const label=n=>n+" % · "+fmt.format(100*n)+" USD";
    document.getElementById("home-first").textContent=label(share);
    document.getElementById("home-second").textContent=label(100-share);
    const equity=(share*.2+(100-share)*.8);
    document.getElementById("guide-pie").style.setProperty("--equity",equity+"%");
    document.getElementById("guide-equity").textContent=label(equity);
    document.getElementById("guide-bonds").textContent=label(100-equity);
    slider.setAttribute("aria-valuetext",label(share));
  }
  slider.addEventListener("input",update);
  document.addEventListener("riskmatch:language",update);
  update();
})();

// Observe each visual independently so a long mobile chapter reveals at reading pace.
(() => {
  const atlas=document.querySelector(".home-atlas");
  if(!atlas||!("IntersectionObserver" in window))return;
  const reveal=new IntersectionObserver(entries=>{
    for(const entry of entries)if(entry.isIntersecting){
      entry.target.classList.add("atlas-enter");
      reveal.unobserve(entry.target);
    }
  },{rootMargin:"0px 0px -8% 0px",threshold:0});
  const sections=Array.from(atlas.querySelectorAll(":scope > section"));
  const links=Array.from(atlas.querySelectorAll(".atlas-nav a"));
  const mark=()=>{
    const readingLine=innerHeight*.42;
    const current=sections.reduce((last,item)=>item.getBoundingClientRect().top<=readingLine?item:last,sections[0]);
    for(const link of links){
      if(link.hash==="#"+current.id)link.setAttribute("aria-current","location");
      else link.removeAttribute("aria-current");
    }
  };
  const position=new IntersectionObserver(mark,{rootMargin:"-40% 0px -57% 0px"});
  for(const section of sections){
    position.observe(section);
    for(const node of section.querySelectorAll("h2,.atlas-savings ol,.atlas-choice,.atlas-flow li,#guide-pie,.atlas-key,.atlas-readout dt,.atlas-readout dd")){
      if(node.parentElement.matches(".atlas-flow,.atlas-savings ol")){
        const index=Array.from(node.parentElement.children).indexOf(node);
        node.style.setProperty("--beat",Math.min(index*110,330)+"ms");
      }
      reveal.observe(node);
    }
  }

  // A decorative cherry rolls along the chapter edge as the reader scrolls.
  const rider=document.createElement("div");
  rider.className="atlas-rider";
  rider.setAttribute("aria-hidden","true");
  rider.innerHTML='<img src="./assets/cherry.png" alt="">';
  for(let index=0;index<9;index++){
    const fruit=document.createElement("img");
    fruit.src="./assets/cherry.png";fruit.alt="";fruit.className="atlas-fragment";
    const angle=index*2*Math.PI/9;
    fruit.style.setProperty("--dx",Math.cos(angle)*100+"px");
    fruit.style.setProperty("--dy",Math.sin(angle)*100+"px");
    fruit.style.setProperty("--spin",(index*83-180)+"deg");
    rider.append(fruit);
  }
  atlas.append(rider);
  const motion=matchMedia("(prefers-reduced-motion: reduce)");
  let frame=0,lastChapter=-1,finished=false;
  function follow(){
    frame=0;
    if(!atlas.getClientRects().length){rider.hidden=true;return;}
    mark();
    if(motion.matches){rider.hidden=true;return;}
    const rect=atlas.getBoundingClientRect();
    const line=innerHeight*.65;
    const distance=Math.max(0,Math.min(rect.height-65,line-rect.top));
    const visible=rect.top<line&&rect.bottom>line;
    rider.hidden=!visible;
    if(!visible)return;
    const chapter=sections.reduce((n,section,i)=>section.getBoundingClientRect().top<=line?i:n,0);
    const progress=Math.max(0,Math.min(1,distance/Math.max(1,rect.height-65)));
    rider.style.setProperty("--travel",distance+"px");
    rider.style.setProperty("--roll",progress*1440+"deg");
    if(chapter!==lastChapter){
      lastChapter=chapter;
      rider.classList.remove("atlas-hop");
      rider.firstElementChild.getBoundingClientRect();
      rider.classList.add("atlas-hop");
    }
    const finale=sections[sections.length-1].getBoundingClientRect();
    const reached=finale.top<line&&line-finale.top>Math.min(finale.height*.4,innerHeight*.3);
    if(reached&&!finished){finished=true;rider.classList.add("atlas-burst");}
    else if(!reached&&finished){finished=false;rider.classList.remove("atlas-burst");}
  }
  function schedule(){if(!frame)frame=requestAnimationFrame(follow);}
  window.addEventListener("scroll",schedule,{passive:true});
  window.addEventListener("resize",schedule);
  motion.addEventListener("change",schedule);
  position.observe(atlas);
  const visibility=new IntersectionObserver(schedule);
  visibility.observe(atlas);
  schedule();
})();
