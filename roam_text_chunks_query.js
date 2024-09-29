;(()=>{
  // Define the function in the global scope so it can be called from anywhere
  window.getLinkedPages = (pageTitle) => {
    let linkedPages = new Set();
    
    // Query for backlinks
    window.roamAlphaAPI.q(`
      [:find ?linkedPage
       :where
       [?e :node/title "${pageTitle}"]
       [?r :block/refs ?e]
       [?r :block/page ?p]
       [?p :node/title ?linkedPage]]
    `).forEach(result => linkedPages.add(result[0]));

    // Query for outgoing links
    window.roamAlphaAPI.q(`
      [:find ?linkedPage
       :where
       [?e :node/title "${pageTitle}"]
       [?b :block/page ?e]
       [?b :block/refs ?r]
       [?r :node/title ?linkedPage]]
    `).forEach(result => linkedPages.add(result[0]));

    return Array.from(linkedPages);
  };

  const createDialog = (title, fields, callback) => {
  const dialog = document.createElement('div');
  dialog.className = 'bp3-dialog-container';
  dialog.style.position = 'fixed';
  dialog.style.top = '0';
  dialog.style.left = '0';
  dialog.style.right = '0';
  dialog.style.bottom = '0';
  dialog.style.display = 'flex';
  dialog.style.justifyContent = 'center';
  dialog.style.alignItems = 'center';
  dialog.style.backgroundColor = 'rgba(0, 0, 0, 0.3)';
  dialog.style.zIndex = '1000';

  const content = document.createElement('div');
  content.className = 'bp3-dialog';
  content.style.width = '50%';
  content.style.maxWidth = '600px';
  content.style.padding = '20px';
  content.style.backgroundColor = 'white';
  content.style.borderRadius = '3px';
  content.style.boxShadow = '0 0 0 1px rgba(16, 22, 26, 0.1), 0 4px 8px rgba(16, 22, 26, 0.2), 0 18px 46px 6px rgba(16, 22, 26, 0.2)';

  content.innerHTML = `<h3 class="bp3-heading">${title}</h3>`;

  fields.forEach(field => {
    const label = document.createElement('label');
    label.className = 'bp3-label';
    label.textContent = field.label;

    let input;
    if (field.type === 'textarea') {
      input = document.createElement('textarea');
      input.className = 'bp3-input';
      input.style.width = '100%';
      input.style.height = '200px';  // Increased height for textarea
      input.value = field.value || '';
    } else {
      input = document.createElement('input');
      input.className = 'bp3-input';
      input.type = field.type;
      input.value = field.value || '';
    }
    input.name = field.name;

    label.appendChild(input);
    content.appendChild(label);
  });

  const buttonContainer = document.createElement('div');
  buttonContainer.style.marginTop = '20px';
  buttonContainer.style.display = 'flex';
  buttonContainer.style.justifyContent = 'flex-end';

  const okButton = document.createElement('button');
  okButton.className = 'bp3-button bp3-intent-primary';
  okButton.textContent = 'OK';
  okButton.addEventListener('click', () => {
    const data = {};
    fields.forEach(field => {
      data[field.name] = content.querySelector(`[name="${field.name}"]`).value;
    });
    callback(data);
    document.body.removeChild(dialog);
  });

  buttonContainer.appendChild(okButton);
  content.appendChild(buttonContainer);
  dialog.appendChild(content);
  document.body.appendChild(dialog);
};


  // Function to get linked pages with weights
window.getWeightedLinkedPages = async (pageTitle) => {
  const result = await window.roamAlphaAPI.q(`
    [:find ?childString
     :where
     [?page :node/title "${pageTitle}"]
     [?page :block/children ?parentBlock]
     [?parentBlock :block/string "Weighted Linked Pages"]
     [?parentBlock :block/children ?childBlock]
     [?childBlock :block/string ?childString]]
  `);

  return result.map(([childString]) => {
    const [page, weight] = childString.split(': ');
    return { page, weight: parseInt(weight, 10) };
  });
};

  // Function to get weighted pages recursively
const getRecursiveWeightedPages = async (pageTitle, depth = 2) => {
  if (depth === 0) return [];

  const directLinks = await window.getWeightedLinkedPages(pageTitle);
  const result = [...directLinks];

  for (const { page, weight } of directLinks) {
    const subLinks = await getRecursiveWeightedPages(page, depth - 1);
    for (const subLink of subLinks) {
      const existingLink = result.find(link => link.page === subLink.page);
      if (existingLink) {
        existingLink.weight += subLink.weight;
      } else {
        result.push({
          page: subLink.page,
          weight: subLink.weight + weight
        });
      }
    }
  }

  return result;
};
  
  // Function to save weighted pages
const saveWeightedPages = async (pageTitle, weightedPages) => {
  weightedPages.sort((a, b) => b.weight - a.weight);

  try {
    const pageUid = await window.roamAlphaAPI.q(`[:find ?uid .
                                                  :where [?e :node/title "${pageTitle}"]
                                                         [?e :block/uid ?uid]]`);
    if (pageUid) {
      const blockString = "Weighted Linked Pages";
      const parentBlockUid = window.roamAlphaAPI.util.generateUID();
      
      await window.roamAlphaAPI.createBlock({
        location: { "parent-uid": pageUid, order: 0 },
        block: { string: blockString, uid: parentBlockUid }
      });

      for (const { page, weight } of weightedPages) {
        const childBlockUid = window.roamAlphaAPI.util.generateUID();
        await window.roamAlphaAPI.createBlock({
          location: { "parent-uid": parentBlockUid, order: 0 },
          block: { string: `${page}: ${weight}`, uid: childBlockUid }
        });
      }

      createDialog('Success', [
        {label: 'Message:', type: 'text', name: 'message', value: 'Weighted pages saved successfully.'}
      ], () => {});
    } else {
      throw new Error('Page not found');
    }
  } catch (error) {
    console.error('Error saving weighted pages:', error);
    createDialog('Error', [
      {label: 'Message:', type: 'text', name: 'message', value: `Failed to save weighted pages: ${error.message}`}
    ], () => {});
  }
};

  // Function to add weights and save results
window.addWeightsAndSave = async (pageTitle) => {
  const linkedPages = window.getLinkedPages(pageTitle);
  
  if (linkedPages.length === 0) {
    createDialog('No Linked Pages', [
      {label: 'Message:', type: 'text', name: 'message', value: `No linked pages found for "${pageTitle}".`}
    ], () => {});
    return;
  }

  const weightedPages = [];

  const addWeight = (index) => {
    if (index < linkedPages.length) {
      const page = linkedPages[index];
      createDialog(`Add weight for ${page}`, [
        {label: 'Weight (0-100):', type: 'number', name: 'weight', value: '50'}
      ], async (data) => {
        weightedPages.push({ page, weight: parseInt(data.weight, 10) });
        addWeight(index + 1);
      });
    } else {
      saveWeightedPages(pageTitle, weightedPages);
    }
  };

  addWeight(0);
};
  
  // Function to query saved weighted pages
window.getWeightedPages = async (pageTitle) => {
  const result = await window.roamAlphaAPI.q(`
    [:find ?childString
     :where
     [?page :node/title "${pageTitle}"]
     [?page :block/children ?parentBlock]
     [?parentBlock :block/string "Weighted Linked Pages"]
     [?parentBlock :block/children ?childBlock]
     [?childBlock :block/string ?childString]]
  `);

  return result.map(([childString]) => {
    const [page, weight] = childString.split(': ');
    return { page, weight: parseInt(weight, 10) };
  });
};

  // Function to display weighted pages
window.displayWeightedPages = async (pageTitle) => {
  try {
    const weightedPages = await getRecursiveWeightedPages(pageTitle);
    if (weightedPages.length === 0) {
      createDialog('No Weighted Pages', [
        {label: 'Message:', type: 'text', name: 'message', value: `No weighted pages found for "${pageTitle}".`}
      ], () => {});
      return;
    }

    const sortedPages = weightedPages.sort((a, b) => a.weight - b.weight); // Sort in ascending order
    const message = sortedPages.map(({ page, weight }) => `${page}: ${weight}`).join('\n');

    createDialog('Weighted Linked Pages', [
      {label: `Pages (for ${pageTitle}):`, type: 'textarea', name: 'pages', value: message}
    ], () => {});
  } catch (error) {
    console.error('Error displaying weighted pages:', error);
    createDialog('Error', [
      {label: 'Message:', type: 'text', name: 'message', value: `Failed to display weighted pages: ${error.message}`}
    ], () => {});
  }
};

  // Add commands to the command palette
  window.roamAlphaAPI.ui.commandPalette.addCommand({
    label: "Add Weights to Linked Pages",
    callback: () => {
      createDialog('Enter Page Title', [
        {label: 'Page Title:', type: 'text', name: 'pageTitle'}
      ], (data) => {
        if (data.pageTitle) {
          window.addWeightsAndSave(data.pageTitle);
        }
      });
    }
  });

  window.roamAlphaAPI.ui.commandPalette.addCommand({
    label: "Display Weighted Linked Pages",
    callback: () => {
      createDialog('Enter Page Title', [
        {label: 'Page Title:', type: 'text', name: 'pageTitle'}
      ], (data) => {
        if (data.pageTitle) {
          window.displayWeightedPages(data.pageTitle);
        }
      });
    }
  });
})();
