class PreRenderHandler extends Paged.Handler {
  constructor(chunker, polisher, caller) {
    super(chunker, polisher, caller);
    this.diagramCount = 0;
  }

  async beforeParsed(content) {
    // Handle footnotes
    const footnoteRefs = content.querySelectorAll('a.footnote-ref');
    const footnoteSection = content.querySelector('.footnote');
    
    console.log('Found footnote refs:', footnoteRefs);
    console.log('Found footnote section:', footnoteSection);
    
    if (footnoteRefs.length > 0 && footnoteSection) {
    
      // Get all footnotes
      const footnotes = footnoteSection.querySelectorAll('ol > li');
      console.log('Found footnotes:', footnotes);
      
      // Process each reference
      footnoteRefs.forEach(ref => {
        const href = ref.getAttribute('href');
        const id = href.substring(1); // Remove the # from the href
        console.log('Processing reference:', ref);
        console.log('Looking for footnote with id:', id);
        
        const footnote = content.querySelector(`#${CSS.escape(id)}`);

        // move the footnote to just after the reference
        if (footnote) {
          console.log('Found footnote:', footnote);
          console.log('Footnote content:', footnote.innerHTML);
          // find the parent of the reference
          const parent = ref.parentNode;
          console.log('Reference parent:', parent);
          
          // replace the parent with a span of class footnote, containing the content of the footnote
          const span = document.createElement('span');
          span.classList.add('footnote');
          
          // remove any element of class footnote-backref from the content of the span

          const backRefElement = footnote.querySelector('.footnote-backref');
          console.log('Found backref element:', backRefElement);
          let href = null;
          if (backRefElement) {
            // get href from backRefElement
            href = backRefElement.getAttribute('href').replace('#', '');
            console.log('Href:', href);
            // remove the backRefElement
            backRefElement.remove();
          }

          span.innerHTML = footnote.innerHTML;
          console.log('Created span with content:', span);
          
          // if we have an href, find all elements with that href as id and replace them with a copy of the span
          if (href) {
            console.log('Href found, replacing elements with span:', href);
            const backRefElements = content.querySelectorAll(`#${CSS.escape(href)}`);
            console.log('Found backref elements:', backRefElements);
            backRefElements.forEach(el => {
              console.log('Replacing element with span:', el);
              el.replaceWith(span.cloneNode(true));
            });
          }
          else {
            // add as sibling of the parent then remove the parent
            parent.parentNode.insertBefore(span, parent.nextSibling);
            parent.remove();
            console.log('Moved footnote content after reference');
          }
          

          // if the parent of the footnote parent is a footnote div, and there are no other footnotes in the parent, then remove the parent
          if (footnote.parentNode.parentNode.classList.contains('footnote') && footnote.parentNode.parentNode.querySelectorAll('ol > li').length === 1) {
            footnote.parentNode.parentNode.remove();
          }
          else {
            // remove the footnote from the content
            footnote.remove();
          }


          // output the parent of the span
          console.log('Parent of span:', span.parentNode);
        }
      });
    }

    // Convert tabbed sets to sequential content
    const tabbedSets = content.querySelectorAll('.tabbed-set');
    tabbedSets.forEach(tabbedSet => {
      // Create a container for the sequential content
      const container = document.createElement('div');
      container.style.display = 'block';
      
      // Get the tab labels and blocks
      const labels = Array.from(tabbedSet.querySelectorAll('.tabbed-labels label'));
      const blocks = Array.from(tabbedSet.querySelectorAll('.tabbed-block'));
      
      // Combine labels with their content
      blocks.forEach((block, index) => {
        const label = labels[index];
        if (label) {
          const heading = document.createElement('h5');
          label.textContent = label.textContent;
          label.classList.add('tabbed-labels-print');
          container.appendChild(label);
        }
        
        const content = block.cloneNode(true);
        content.className = '';
        content.style.display = 'block';
        content.style.marginBottom = '1em';
        container.appendChild(content);
      });

      // Replace the tabbed set with the sequential content
      tabbedSet.parentNode.replaceChild(container, tabbedSet);
    });

    // Process MathJax
    if (window.MathJax) {
      try {
        // Find all math elements
        const mathElements = content.querySelectorAll('.arithmatex');
        for (const element of mathElements) {
          let math = element.textContent;
          // Extract just the math content
          let isDisplay = false;
          if (math.includes('\\[') && math.includes('\\]')) {
            math = math.substring(math.indexOf('\\[') + 2, math.indexOf('\\]'));
            isDisplay = true;
          } else if (math.includes('\\(') && math.includes('\\)')) {
            math = math.substring(math.indexOf('\\(') + 2, math.indexOf('\\)'));
            isDisplay = false;
          }
          
          // Create a new element for the rendered math
          const rendered = document.createElement('div');
          rendered.innerHTML = await MathJax.tex2chtml(math, {display: isDisplay}).outerHTML;
          // Replace the original element with the rendered math
          element.parentNode.replaceChild(rendered.firstChild, element);
        }
      } catch (error) {
        console.error('Failed to render MathJax:', error);
      }
    }

    // Render Mermaid diagrams
    const mermaidElements = content.querySelectorAll('.mermaid');
    await Promise.all(
      Array.from(mermaidElements).map(async (element) => {
        const graphCode = element.textContent;
        try {
          const id = `diagram-${this.diagramCount++}`;
          const { svg } = await mermaid.render(id, graphCode);
          
          // Create a container for the SVG
          const container = document.createElement('div');
          container.style.width = '100%';
          container.style.maxHeight = 'none';
          container.style.overflow = 'visible';
          container.style.display = 'block';
          container.style.marginBottom = '1em';  // Add space after diagram
          container.style.pageBreakInside = 'avoid'; // Prevent diagrams from breaking across pages
          container.innerHTML = svg;

          // Process the SVG
          const svgElement = container.querySelector('svg');
          if (svgElement) {
            // Ensure SVG takes full width and maintains aspect ratio
            svgElement.style.width = '100%';
            svgElement.style.height = 'auto';
            svgElement.style.maxWidth = 'none';
            svgElement.style.display = 'block'; // Ensure SVG is block-level
            svgElement.setAttribute('preserveAspectRatio', 'xMinYMin');
            
            // If SVG doesn't have a viewBox, create one from width/height
            if (!svgElement.getAttribute('viewBox')) {
              const width = svgElement.getAttribute('width') || svgElement.getBoundingClientRect().width;
              const height = svgElement.getAttribute('height') || svgElement.getBoundingClientRect().height;
              svgElement.setAttribute('viewBox', `0 0 ${width} ${height}`);
            }
          }

          element.replaceWith(container);
        } catch (error) {
          console.error('Failed to render mermaid diagram:', error);
          element.innerHTML = `<pre>${graphCode}</pre>`;
        }
      })
    );

    // Initialize table sorting
    const tables = content.querySelectorAll("article table:not([class])");
    tables.forEach(function(table) {
      if (typeof Tablesort !== 'undefined') {
        new Tablesort(table);
      }
    });
  }
}

// Register the handler with Paged.js
Paged.registerHandlers(PreRenderHandler); 