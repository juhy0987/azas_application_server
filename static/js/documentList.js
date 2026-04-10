// ── Document list helpers ────────────────────────────────────────────────────

import { apiUpdateTitle } from "./api.js";

export function closeAllMenus(list) {
  list.querySelectorAll('.document-menu').forEach((m) => (m.hidden = true));
}

export function setActiveItem(list, targetItem) {
  list.querySelectorAll('.document-item').forEach((btn) => btn.classList.remove('is-active'));
  const btn = targetItem.querySelector(':scope > .document-row > .document-item');
  if (btn) btn.classList.add('is-active');
}

/**
 * Replace the document-item button inside listItem with an <input> for inline
 * title editing. Commits on Enter or blur; cancels (keeps original) on Escape.
 */
export function enterInlineEdit(listItem, docId, initialTitle, list, onSelect) {
  const existingBtn = listItem.querySelector(':scope > .document-row > .document-item');
  const menuBtn = listItem.querySelector(':scope > .document-row > .document-menu-btn');

  const input = document.createElement('input');
  input.type = 'text';
  input.setAttribute('size', '1');
  input.className = 'document-title-input';
  input.value = initialTitle;
  existingBtn.replaceWith(input);

  if (menuBtn) menuBtn.hidden = true;

  input.focus();
  input.select();

  let exited = false;

  function restoreButton(title) {
    if (exited) return;
    exited = true;

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'document-item is-active';
    btn.textContent = title;
    btn.addEventListener('click', () => {
      closeAllMenus(list);
      setActiveItem(list, listItem);
      onSelect(docId);
    });
    input.replaceWith(btn);
    if (menuBtn) menuBtn.hidden = false;
  }

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      const newTitle = input.value.trim() || '새 문서';
      apiUpdateTitle(docId, newTitle).catch(console.error);
      restoreButton(newTitle);
    } else if (e.key === 'Escape') {
      restoreButton(initialTitle);
    }
  });

  input.addEventListener('blur', () => {
    const newTitle = input.value.trim() || '새 문서';
    if (!exited) apiUpdateTitle(docId, newTitle).catch(console.error);
    restoreButton(newTitle);
  });
}

/**
 * Build and append a single document list item (and its children recursively).
 *
 * @param {HTMLElement} list        - Parent <ul> to append into
 * @param {object}      docInfo     - Document data including .children[]
 * @param {object}      handlers    - { onSelect, onDelete, onAddChild }
 * @param {number}      depth       - Nesting depth (0 = root)
 * @returns {HTMLLIElement}
 */
export function addDocumentItem(list, docInfo, handlers, depth = 0) {
  const { onSelect, onDelete, onAddChild } = handlers;

  const item = document.createElement('li');
  item.dataset.id = docInfo.id;

  const row = document.createElement('div');
  row.className = 'document-row';
  row.style.paddingLeft = depth > 0 ? `${depth * 14}px` : '0';

  // ── Toggle button (> chevron) ─────────────────────────────────────────────
  const toggleBtn = document.createElement('button');
  toggleBtn.type = 'button';
  toggleBtn.className = 'document-toggle-btn';
  toggleBtn.setAttribute('aria-label', '하위 페이지 펼치기/접기');
  toggleBtn.setAttribute('aria-expanded', 'false');
  // Visibility: always present for layout stability; visually shown only when
  // there are children or on hover (via CSS).
  if (docInfo.children && docInfo.children.length > 0) {
    toggleBtn.classList.add('has-children');
  }

  // ── Document select button ────────────────────────────────────────────────
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'document-item';
  btn.textContent = docInfo.title;
  btn.addEventListener('click', () => {
    closeAllMenus(list);
    setActiveItem(list, item);
    onSelect(docInfo.id);
  });

  // ── More (⋯) menu button ──────────────────────────────────────────────────
  const menuBtn = document.createElement('button');
  menuBtn.type = 'button';
  menuBtn.className = 'document-menu-btn';
  menuBtn.setAttribute('aria-label', '더보기');
  menuBtn.textContent = '⋯';

  const menu = document.createElement('div');
  menu.className = 'document-menu';
  menu.hidden = true;

  const addChildBtn = document.createElement('button');
  addChildBtn.type = 'button';
  addChildBtn.className = 'document-menu-action';
  addChildBtn.textContent = '하위 페이지 추가';
  addChildBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    menu.hidden = true;
    onAddChild(docInfo.id, item, childrenList, depth + 1);
  });

  const deleteBtn = document.createElement('button');
  deleteBtn.type = 'button';
  deleteBtn.className = 'document-menu-delete';
  deleteBtn.textContent = '삭제';
  deleteBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    menu.hidden = true;
    onDelete(docInfo.id, item);
  });

  menuBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const wasHidden = menu.hidden;
    closeAllMenus(list);
    menu.hidden = !wasHidden;
  });

  menu.appendChild(addChildBtn);
  menu.appendChild(deleteBtn);
  row.appendChild(toggleBtn);
  row.appendChild(btn);
  row.appendChild(menuBtn);
  row.appendChild(menu);
  item.appendChild(row);

  // ── Children list ─────────────────────────────────────────────────────────
  const childrenList = document.createElement('ul');
  childrenList.className = 'document-children';
  childrenList.hidden = true;
  item.appendChild(childrenList);

  // Render existing children (collapsed by default)
  if (docInfo.children && docInfo.children.length > 0) {
    docInfo.children.forEach((child) =>
      addDocumentItem(childrenList, child, handlers, depth + 1)
    );
  }

  // ── Toggle expand/collapse ────────────────────────────────────────────────
  toggleBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const willExpand = !toggleBtn.classList.contains('is-expanded');
    toggleBtn.classList.toggle('is-expanded', willExpand);
    toggleBtn.setAttribute('aria-expanded', String(willExpand));
    childrenList.hidden = !willExpand;
  });

  list.appendChild(item);
  return item;
}
