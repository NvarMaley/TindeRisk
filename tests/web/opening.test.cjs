const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const web = path.resolve(__dirname, "../../apps/web");

test("opening is mandatory, starts audio and waits exactly five seconds",()=>{
  const listeners={}, timeline=[], tracks=[], events=[];
  let targetPage=null;
  class Element {
    constructor(){this.dataset={};this.hidden=false;this.listeners={};}
    addEventListener(name,callback){this.listeners[name]=callback;}
    setAttribute(){}
    focus(){}
  }
  const ids=Object.fromEntries(["opening","intro-start","intro-loading","save-slot","sound-toggle","intro-sound-toggle","save-sound-toggle","sound-waves"].map(id=>[id,new Element()]));
  ids.opening.dataset.phase="idle";
  ids["intro-loading"].hidden=true;
  class Audio {
    constructor(src){this.src=src;this.paused=true;this.listeners={};tracks.push(this);}
    play(){this.paused=false;this.listeners.play?.();return Promise.resolve();}
    pause(){this.paused=true;this.listeners.pause?.();}
    addEventListener(name,fn){this.listeners[name]=fn;}
  }
  const ctx={Audio,window:{RM:{t:x=>x},addEventListener(){}},Event:class{constructor(type){this.type=type;}},
    document:{
      getElementById:id=>ids[id],body:{removeAttribute(){}},
      addEventListener:(name,fn)=>{listeners[name]=fn;},
      removeEventListener:name=>{delete listeners[name];},
      dispatchEvent:event=>{events.push(event.type);listeners[event.type]?.(event);},
    },
    setTimeout:(fn,ms)=>{timeline.push({fn,ms});return 1;},clearTimeout(){},page:name=>{targetPage=name;}
  };
  vm.createContext(ctx);
  for(const file of ["theme.js","opening.js"])vm.runInContext(fs.readFileSync(path.join(web,file),"utf8"),ctx);
  assert.equal(tracks[0].paused,true);
  assert.equal(targetPage,null);
  listeners.keydown({key:"Enter",target:{},preventDefault(){}});
  assert.equal(tracks[0].paused,false);
  assert.ok(events.includes("riskmatch:intro-start"));
  assert.equal(ids.opening.dataset.phase,"rising");
  assert.equal(ids["intro-loading"].hidden,false);
  assert.equal(timeline.length,1);
  assert.equal(timeline[0].ms,5000);
  assert.equal(targetPage,null);
  ids["intro-start"].listeners.click();
  assert.equal(timeline.length,1);
  timeline[0].fn();
  assert.equal(targetPage,"saves");
  assert.equal(ids.opening.hidden,true);
  assert.doesNotMatch(fs.readFileSync(path.join(web,"index.html"),"utf8"),/intro-skip|skipIntro/);
});
