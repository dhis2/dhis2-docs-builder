window.MathJax = {
  tex: {
    processEscapes: false,
    processEnvironments: true
  },
  options: {
    ignoreHtmlClass: ".*|",
    processHtmlClass: "arithmatex"
  },
  startup: {
    pageReady: () => {
      return Promise.resolve();
    }
  }
}; 