const root = document.getElementById("root");
const paths = [
  "streamlit_app.py",
  "model.py",
  "riskmatch/__init__.py",
  "riskmatch/optimization/__init__.py",
  "riskmatch/optimization/mean_variance.py",
];
try {
  const [{mount}, files] = await Promise.all([
    import("https://cdn.jsdelivr.net/npm/@stlite/browser@0.83.0/build/stlite.js"),
    Promise.all(paths.map(async path => {
      const response = await fetch(path);
      if (!response.ok) throw new Error(`HTTP ${response.status}: ${path}`);
      return [path, await response.text()];
    })),
  ]);
  root.replaceChildren();
  mount({
    entrypoint: "streamlit_app.py",
    requirements: ["numpy", "scipy", "pandas"],
    files: Object.fromEntries(files),
  }, root);
} catch (error) {
  console.error(error);
  root.textContent = "Le moteur de démonstration n’a pas pu démarrer. Recharge la page pour réessayer.";
}
