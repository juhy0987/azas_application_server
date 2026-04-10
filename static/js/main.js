// ── App entry point ───────────────────────────────────────────────────────────

import {
  fetchDocuments,
  fetchDocument,
  apiCreateDocument,
  apiCreateChildDocument,
  apiDeleteDocument,
  apiCreateBlock,
  apiMoveBlock,
} from "./api.js";
import { callbacks, renderBlock, renderDocument, focusBlock } from "./blockRenderers.js";
import { addDocumentItem, closeAllMenus, setActiveItem, enterInlineEdit } from "./documentList.js";
import { initSidebar } from "./sidebar.js";

async function initGallery() {
  const root = document.getElementById('block-root');
  const list = document.getElementById('document-list');
  const newDocBtn = document.getElementById('new-document-btn');

  let activeDocId = null;

  // ── Wire up renderer callbacks ────────────────────────────────────────────
  callbacks.navigateTo = (documentId) => {
    const targetItem = list.querySelector(`li[data-id="${documentId}"]`);
    if (targetItem) {
      closeAllMenus(list);
      setActiveItem(list, targetItem);
    }
    loadDocument(documentId);
  };

  callbacks.reloadDocument = () => {
    if (activeDocId) loadDocument(activeDocId);
  };

  // ── Document loader ───────────────────────────────────────────────────────
  async function loadDocument(documentId, { focusBlockId = null } = {}) {
    activeDocId = documentId;

    callbacks.addBlockAfter = async (type, afterBlockId, parentBlockId = null) => {
      const newBlock = await apiCreateBlock(activeDocId, type, parentBlockId);
      const afterWrapper = document.querySelector(`[data-block-id="${afterBlockId}"]`);
      if (afterWrapper) {
        const newWrapper = renderBlock(newBlock, parentBlockId);
        afterWrapper.after(newWrapper);
        const nextWrapper = newWrapper.nextElementSibling;
        if (nextWrapper?.dataset?.blockId) {
          await apiMoveBlock(newBlock.id, nextWrapper.dataset.blockId);
        }
        focusBlock(newWrapper);
      }
    };

    const addBlock = async (type, parentBlockId = null) => {
      const newBlock = await apiCreateBlock(activeDocId, type, parentBlockId);
      const containerEl = parentBlockId
        ? document.querySelector(`[data-block-id="${parentBlockId}"] .container-children`)
        : root;
      if (containerEl) {
        const newWrapper = renderBlock(newBlock, parentBlockId);
        containerEl.appendChild(newWrapper);
        focusBlock(newWrapper);
      }
    };
    callbacks.addBlock = addBlock;

    try {
      const payload = await fetchDocument(documentId);

      const rootBlocks = payload.blocks;
      const lastBlock = rootBlocks[rootBlocks.length - 1];
      if (!lastBlock || lastBlock.type !== 'text') {
        const newBlock = await apiCreateBlock(activeDocId, 'text');
        await loadDocument(documentId, { focusBlockId: focusBlockId ?? newBlock.id });
        return;
      }

      renderDocument(payload);
      if (focusBlockId) {
        const targetWrapper = root.querySelector(`[data-block-id="${focusBlockId}"]`);
        const targetBlock = targetWrapper?.querySelector('.notion-block');
        if (targetBlock) {
          const focusTarget = targetBlock.classList.contains('notion-text')
            ? targetBlock
            : (targetBlock.querySelector('.notion-caption, .container-title') ?? targetBlock);
          focusTarget.click();
        }
      }
    } catch (err) {
      const p = document.createElement('p');
      p.className = 'error-state';
      p.textContent = `문서를 불러오지 못했습니다: ${err.message}`;
      root.replaceChildren(p);
    }
  }

  function showEmptyState() {
    activeDocId = null;
    document.getElementById('page-title').textContent = '';
    document.getElementById('page-subtitle').textContent = '';
    const p = document.createElement('p');
    p.className = 'empty-state';
    p.textContent = '문서가 없습니다.';
    root.replaceChildren(p);
  }

  // ── Shared document action handlers ──────────────────────────────────────
  const handlers = {
    onSelect(docId) {
      loadDocument(docId);
    },
    async onDelete(docId, item) {
      const wasActive = docId === activeDocId;
      try {
        await apiDeleteDocument(docId);
        item.remove();

        if (wasActive) {
          const firstItem = list.querySelector('li');
          if (firstItem) {
            setActiveItem(list, firstItem);
            loadDocument(firstItem.dataset.id);
          } else {
            showEmptyState();
          }
        }
      } catch (err) {
        console.error('문서 삭제 실패:', err);
      }
    },
    async onAddChild(parentId, parentItem, childrenList, childDepth) {
      try {
        const newDoc = await apiCreateChildDocument(parentId);

        // Mark toggle button as having children and expand
        const toggleBtn = parentItem.querySelector(':scope > .document-row > .document-toggle-btn');
        if (toggleBtn) {
          toggleBtn.classList.add('has-children', 'is-expanded');
          toggleBtn.setAttribute('aria-expanded', 'true');
        }
        childrenList.hidden = false;

        const childItem = addDocumentItem(childrenList, newDoc, handlers, childDepth);
        closeAllMenus(list);
        setActiveItem(list, childItem);
        activeDocId = newDoc.id;
        document.getElementById('page-title').textContent = newDoc.title;
        document.getElementById('page-subtitle').textContent = '';
        root.innerHTML = '';
        enterInlineEdit(childItem, newDoc.id, newDoc.title, list, (docId) => loadDocument(docId));
      } catch (err) {
        console.error('하위 문서 생성 실패:', err);
      }
    },
  };

  // ── Sidebar ───────────────────────────────────────────────────────────────
  initSidebar(
    document.getElementById('sidebar-tab'),
    document.getElementById('sidebar-panel'),
  );

  document.addEventListener('click', () => {
    closeAllMenus(list);
    document.querySelectorAll('.block-more-menu').forEach((m) => (m.hidden = true));
  });

  // ── Load initial document tree ────────────────────────────────────────────
  try {
    const documents = await fetchDocuments();

    if (documents.length === 0) {
      showEmptyState();
    } else {
      // documents is already a tree (root nodes with .children arrays)
      documents.forEach((doc) => addDocumentItem(list, doc, handlers, 0));
      const firstItem = list.querySelector('li');
      setActiveItem(list, firstItem);
      await loadDocument(documents[0].id);
    }
  } catch (err) {
    const p = document.createElement('p');
    p.className = 'error-state';
    p.textContent = `문서를 불러오지 못했습니다: ${err.message}`;
    root.replaceChildren(p);
  }

  // ── + 새 문서 button ──────────────────────────────────────────────────────
  newDocBtn.addEventListener('click', async () => {
    try {
      const newDoc = await apiCreateDocument();
      const item = addDocumentItem(list, newDoc, handlers, 0);
      closeAllMenus(list);
      setActiveItem(list, item);
      document.getElementById('page-title').textContent = newDoc.title;
      document.getElementById('page-subtitle').textContent = '';
      root.innerHTML = '';
      activeDocId = newDoc.id;
      enterInlineEdit(item, newDoc.id, newDoc.title, list, (docId) => loadDocument(docId));
    } catch (err) {
      console.error('문서 생성 실패:', err);
    }
  });
}

window.addEventListener('DOMContentLoaded', initGallery);
