/* Client-facing investment catalogue. Data acquisition audits live in Sources. */
(() => {
  function load(api) {
    return window.AssetResearch.load(api,new Date().toISOString().slice(0,10));
  }
  window.UniverseView={load,render(){window.AssetResearch.render();}};
})();
