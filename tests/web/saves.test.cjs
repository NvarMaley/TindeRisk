const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const { webcrypto } = require("node:crypto");
const path = require("node:path");

const web = path.resolve(__dirname, "../../apps/web");
class Element {
  constructor(){this.value="";this.children=[];this.options=[];this.dataset={};this.hidden=false;}
  replaceChildren(...children){this.children=children;this.options=children;this.value=children[0]?.value||"";}
  add(option){this.options.push(option);}
  append(...children){this.children.push(...children);}
  addEventListener(name,fn){this[name]=fn;}
  setAttribute(){}
}
class Option { constructor(text,value){this.textContent=text;this.value=value;} }
test("mandatory four-digit saves isolate users, reject wrong PINs and restore their own state",async()=>{
  const ids=Object.fromEntries(["save-form","save-slot","save-current","save-name-label","save-pin-label","save-submit","save-name","save-passphrase","resume-save","error","save-backups"].map(name=>[name,new Element()]));
  const storage=new Map();
  let current={version:1,mandate:{capital:123456,years:10,max_stress_loss:.2,currency:"USD"},answers:{L01:"like"},index:1,swipes:[],activePage:"discovery"};
  let restored=null,error=null,access=false;
  const ctx={
    window:{RM:{language:"en"}},
    crypto:webcrypto,TextEncoder,TextDecoder,Uint8Array,btoa,atob,Option,
    localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},
    document:{createElement:()=>new Element(),addEventListener(){}},
    $:id=>ids[id],t:key=>key,page(){},setSaveSession:open=>{access=open;},
    simulationSnapshot:()=>current,clearSimulation:()=>{current={version:1,mandate:null,answers:{},index:0,swipes:[],activePage:"home"};},
    restoreSimulation:async value=>{restored=value;current=value;return value.activePage;},
    enterSavedStudio:async()=>{access=true;},
    handle:fn=>async(...args)=>{try{error=null;await fn(...args);}catch(e){error=e.message;}},
  };
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(web,"saves.js"),"utf8"),ctx);
  const form=ids["save-form"],slot=ids["save-slot"];
  const submit=()=>form.onsubmit({preventDefault(){}});
  ids["save-name"].value="fictional test";
  ids["save-passphrase"].value="12345";
  await submit();assert.equal(error,"pinInvalid");assert.equal(access,false);
  ids["save-passphrase"].value="0123";
  await submit();
  assert.equal(error,null);
  assert.equal(access,true);assert.equal(current.mandate,null);
  current={version:1,mandate:{capital:123456,years:10,max_stress_loss:.2,currency:"USD"},answers:{L01:"like"},index:1,swipes:[],activePage:"discovery"};
  const stored=[...storage.values()][0];
  const entry=JSON.parse(stored)[0];
  assert.ok(entry.ciphertext&&entry.salt&&entry.iv);assert.equal(entry.version,2);
  const lock=ids["save-current"].children[2];
  await lock.onclick();
  assert.equal(access,false);assert.equal(current.mandate,null);
  assert.ok(![...storage.values()][0].includes('"capital":123456'));
  const encryptedBackup=JSON.stringify({format:"riskmatch-encrypted-backup-v1",entries:JSON.parse([...storage.values()][0])});
  storage.clear();
  let restoreFile=ids["save-backups"].children[1];
  restoreFile.files=[{size:encryptedBackup.length,text:async()=>encryptedBackup}];
  await restoreFile.onchange();assert.equal(error,null);
  assert.equal(JSON.parse([...storage.values()][0]).length,1);
  restoreFile=ids["save-backups"].children[1];
  restoreFile.files=[{size:encryptedBackup.length,text:async()=>encryptedBackup}];
  await restoreFile.onchange();assert.equal(JSON.parse([...storage.values()][0]).length,1);
  ids["save-name"].value="second user";ids["save-passphrase"].value="4567";await submit();
  assert.equal(error,null);assert.equal(current.mandate,null);assert.equal(access,true);
  await ids["save-current"].children[2].onclick();
  assert.equal(JSON.parse([...storage.values()][0]).length,2);
  slot.value=entry.id;slot.change();
  ids["save-passphrase"].value="9999";await submit();
  assert.equal(error,"saveError");assert.equal(access,false);
  ids["save-passphrase"].value="0123";await submit();
  assert.equal(error,null);assert.equal(restored.mandate.capital,123456);assert.equal(restored.answers.L01,"like");
  assert.equal(access,true);
  assert.equal(ids["save-passphrase"].value,"");
});

test("all static localization keys have English and French values",()=>{
  const html=fs.readFileSync(path.join(web,"index.html"),"utf8");
  const keys=[...html.matchAll(/data-i18n(?:-label)?="([^"]+)"/g)].map(m=>m[1]);
  const select=new Element(), root={lang:"en"}, storage=new Map();
  const ctx={window:{},localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},
    Event:class{},document:{documentElement:root,querySelectorAll:q=>q==="#language,#intro-language,#save-language"?[select]:[],dispatchEvent(){}}};
  vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(web,"i18n.js"),"utf8"),ctx);
  for(const key of keys)assert.notEqual(ctx.window.RM.t(key),key);
  select.change({target:{value:"fr"}});
  assert.equal(ctx.window.RM.language,"fr");
  for(const key of keys)assert.notEqual(ctx.window.RM.t(key),key);
  assert.equal(ctx.window.RM.t("yourSaves"),"Tes sauvegardes");
  assert.equal(root.lang,"fr");
});

test("save form cannot serialize passphrases into a URL if scripts fail",()=>{
  const html=fs.readFileSync(path.join(web,"index.html"),"utf8");
  const form=html.match(/<form id="save-form"[\s\S]+?<\/form>/)[0];
  assert.match(form,/method="post"/);
  assert.match(form,/onsubmit="return false"/);
  for(const input of form.match(/<input[^>]+>/g))assert.doesNotMatch(input,/\bname=/);
  assert.match(form,/<button[^>]+disabled/);
  assert.match(form,/pattern="\[0-9\]\{4\}"/);
  assert.match(html,/<header[^>]+id="studio-nav" hidden>/);
  assert.doesNotMatch(html,/continueFree/);
});

test("studio routing and navigation remain locked until a save is opened",()=>{
  const names=["home","saves","mandate","discovery","explore","compare"];
  const pages=names.map(id=>Object.assign(new Element(),{id}));
  const ids=new Map();
  const $=id=>{if(!ids.has(id))ids.set(id,new Element());return ids.get(id);};
  const body={dataset:{session:"locked"}};
  const ctx={window:{RM:{t:key=>key}},document:{
    body,getElementById:$,querySelectorAll:q=>q===".page"?pages:[],
    addEventListener(){},dispatchEvent(){},createElement:()=>new Element()
  },Event:class{}};
  vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(web,"app.js"),"utf8"),ctx);
  vm.runInContext('page("home")',ctx);
  assert.equal(pages.find(p=>p.id==="home").hidden,true);
  assert.equal(pages.find(p=>p.id==="saves").hidden,false);
  vm.runInContext('setSaveSession(true);page("home")',ctx);
  assert.equal(body.dataset.session,"unlocked");
  assert.equal($("studio-nav").hidden,false);
  assert.equal(pages.find(p=>p.id==="home").hidden,false);
  vm.runInContext('setSaveSession(false);page("explore")',ctx);
  assert.equal($("studio-nav").hidden,true);
  assert.equal(pages.find(p=>p.id==="explore").hidden,true);
});
