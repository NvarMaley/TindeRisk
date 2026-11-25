/* Local encrypted simulation saves. No network storage, account or password recovery. */
(() => {
  const keyName="riskmatch-v3-encrypted-saves-v1";
  const form=$("save-form"), slot=$("save-slot"), current=$("save-current");
  const nameInput=$("save-name"), passInput=$("save-passphrase"), pinLabel=$("save-pin-label");
  const encoder=new TextEncoder(), decoder=new TextDecoder();
  let unlocked=null, busy=false, pending=Promise.resolve();
  function list(){
    try {
      const items=JSON.parse(localStorage.getItem(keyName)||"[]");
      return Array.isArray(items)?items.filter(x=>x&&typeof x.id==="string"&&typeof x.name==="string"):[];
    }catch{return [];}
  }
  function write(items){try{localStorage.setItem(keyName,JSON.stringify(items));}catch{throw Error("saveUnavailable");}}
  const b64=bytes=>btoa(String.fromCharCode(...new Uint8Array(bytes)));
  const bytes=value=>Uint8Array.from(atob(value),c=>c.charCodeAt(0));
  async function derive(passphrase,salt){
    if(!globalThis.crypto?.subtle)throw Error("saveUnavailable");
    const material=await crypto.subtle.importKey("raw",encoder.encode(passphrase),"PBKDF2",false,["deriveKey"]);
    return crypto.subtle.deriveKey({name:"PBKDF2",salt,iterations:310000,hash:"SHA-256"},material,{name:"AES-GCM",length:256},false,["encrypt","decrypt"]);
  }
  async function encrypt(entry,key,snapshot){
    const iv=crypto.getRandomValues(new Uint8Array(12));
    const ciphertext=await crypto.subtle.encrypt({name:"AES-GCM",iv,additionalData:encoder.encode(entry.id)},key,encoder.encode(JSON.stringify(snapshot)));
    return {...entry,iv:b64(iv),ciphertext:b64(ciphertext)};
  }
  async function decrypt(entry,key){
    const clear=await crypto.subtle.decrypt({name:"AES-GCM",iv:bytes(entry.iv),additionalData:encoder.encode(entry.id)},key,bytes(entry.ciphertext));
    return JSON.parse(decoder.decode(clear));
  }
  function mergeBackup(raw){
    const backup=JSON.parse(raw);
    if(backup.format!=="riskmatch-encrypted-backup-v1"||!Array.isArray(backup.entries)||backup.entries.length>1000)throw Error("saveError");
    const existing=list(),seen=new Set(existing.map(x=>x.id));
    const imported=[];
    for(const entry of backup.entries){
      if(!entry||typeof entry.id!=="string"||!entry.id||typeof entry.name!=="string"||!entry.name.trim()||entry.name.length>120||
        ![1,2].includes(entry.version)||typeof entry.ciphertext!=="string"||bytes(entry.salt).length!==16||bytes(entry.iv).length!==12||bytes(entry.ciphertext).length<16)throw Error("saveError");
      if(!seen.has(entry.id)){seen.add(entry.id);imported.push({id:entry.id,name:entry.name,version:entry.version,salt:entry.salt,iv:entry.iv,ciphertext:entry.ciphertext});}
    }
    write([...existing,...imported]);
    return imported.length;
  }
  function renderBackups(){
    const area=$("save-backups");if(!area)return;area.replaceChildren();
    const fr=window.RM.language==="fr";
    const download=document.createElement("button");download.type="button";download.textContent=fr?"Sauvegarder les profils chiffrés":"Back up encrypted saves";
    download.onclick=handle(async()=>{
      if(unlocked)await persist();
      const blob=new Blob([JSON.stringify({format:"riskmatch-encrypted-backup-v1",entries:list()})],{type:"application/json"});
      const url=URL.createObjectURL(blob),link=document.createElement("a");
      link.href=url;link.download="RiskMatch-encrypted-backup.json";link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    });
    area.append(download);
    if(!unlocked){
      const input=document.createElement("input");input.type="file";input.accept=".json,application/json";
      input.setAttribute("aria-label",fr?"Restaurer les sauvegardes":"Restore encrypted saves");
      input.onchange=handle(async()=>{
        if(unlocked||busy)return;
        const file=input.files?.[0];if(!file||file.size>10_000_000)throw Error("saveError");
        busy=true;
        try{const count=mergeBackup(await file.text());refresh();$("error").textContent=fr?count+" sauvegarde(s) importée(s)":count+" save(s) imported";}
        finally{busy=false;}
      });area.append(input);
    }
  }
  function refresh(){
    const previous=slot.value;
    slot.replaceChildren(new Option(t("newSave"),"new"));
    list().forEach(entry=>slot.add(new Option(entry.name,entry.id)));
    if([...slot.options].some(o=>o.value===previous))slot.value=previous;
    const creating=slot.value==="new";
    $("save-name-label").hidden=!creating;
    nameInput.required=creating;
    const legacy=!creating&&list().find(entry=>entry.id===slot.value)?.version===1;
    pinLabel.dataset.i18n=legacy?"legacyPassphrase":"pin";pinLabel.textContent=t(pinLabel.dataset.i18n);
    passInput.inputMode=legacy?"text":"numeric";
    passInput.minLength=legacy?8:4;passInput.maxLength=legacy?128:4;passInput.pattern=legacy?".{8,128}":"[0-9]{4}";
    $("save-submit").dataset.i18n=creating?"createSave":"unlockSave";
    $("save-submit").textContent=t($("save-submit").dataset.i18n);
    form.hidden=Boolean(unlocked);
    $("resume-save").hidden=!unlocked;
    current.replaceChildren();
    if(unlocked){
      const label=document.createElement("span");label.textContent=t("saveActive")+": "+unlocked.entry.name;
      const save=document.createElement("button");save.type="button";save.textContent=t("saveNow");
      save.onclick=handle(async()=>{await persist();$("error").textContent=t("saveDone");});
      const lock=document.createElement("button");lock.type="button";lock.textContent=t("lockSave");
      lock.onclick=handle(async()=>{
        if(busy)return;busy=true;
        try{
          await persist();
          unlocked=null;setSaveSession(false);clearSimulation();slot.value="new";refresh();page("saves");
        }finally{busy=false;}
      });
      current.append(label,save,lock);
    }
    renderBackups();
  }
  function persist(){
    if(!unlocked)return Promise.resolve();
    const session=unlocked;
    const snapshot=JSON.parse(JSON.stringify(simulationSnapshot()));
    const job=pending.catch(()=>{}).then(async()=>{
      const updated=await encrypt(session.entry,session.key,snapshot);
      const entries=list();
      if(!entries.some(entry=>entry.id===updated.id))throw Error("saveUnavailable");
      write(entries.map(entry=>entry.id===updated.id?updated:entry));
      session.entry=updated;
    });
    pending=job;
    return job;
  }
  const blankSnapshot=()=>({version:1,mandate:null,answers:{},index:0,swipes:[],activePage:"home"});
  slot.addEventListener("change",refresh);
  form.onsubmit=handle(async event=>{
    event.preventDefault();
    if(busy||unlocked)return;
    busy=true;$("save-submit").disabled=true;
    const passphrase=passInput.value;
    try{
      if(slot.value==="new"){
        if(!/^\d{4}$/.test(passphrase))throw Error("pinInvalid");
        const name=nameInput.value.trim();
        if(!name)throw Error("saveNameRequired");
        if(!globalThis.crypto?.subtle)throw Error("saveUnavailable");
        const salt=crypto.getRandomValues(new Uint8Array(16));
        const entry={id:crypto.randomUUID(),name,salt:b64(salt),version:2};
        const key=await derive(passphrase,salt);
        const encrypted=await encrypt(entry,key,blankSnapshot());
        write([...list(),encrypted]);clearSimulation();unlocked={entry:encrypted,key};
        await enterSavedStudio("home");
      }else{
        const entry=list().find(x=>x.id===slot.value);
        if(!entry)throw Error("saveError");
        if(entry.version!==1&&!/^\d{4}$/.test(passphrase))throw Error("pinInvalid");
        let key,snapshot;
        try{key=await derive(passphrase,bytes(entry.salt));snapshot=await decrypt(entry,key);}
        catch{throw Error("saveError");}
        clearSimulation();const target=await restoreSimulation(snapshot);unlocked={entry,key};
        await enterSavedStudio(target);
      }
    }finally{passInput.value="";busy=false;$("save-submit").disabled=false;refresh();}
  });
  document.addEventListener("riskmatch:changed",()=>{if(unlocked&&!busy)persist().catch(()=>{$("error").textContent=t("saveFailed");});});
  document.addEventListener("riskmatch:language",refresh);
  document.addEventListener("riskmatch:saves",refresh);
  refresh();
  $("save-submit").disabled=false;
})();
