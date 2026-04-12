// ── URL Embed Block ───────────────────────────────────────────────────────────
//
// 상태 흐름:
//   pending → (URL 입력 + Enter) → 서버 fetch → success | error
//   error   → (재시도 버튼 클릭) → 서버 fetch → success | error
//   success → 북마크 카드 표시, 클릭 시 새 탭으로 이동
//             편집 버튼(✎) 클릭 → URL 재입력 모드로 전환

import { apiFetchUrlEmbed } from "../api.js";

export const type = "url_embed";

/**
 * @param {object} block  - 서버에서 받은 블록 데이터
 * @returns {HTMLElement}
 */
export function create(block) {
  const template = document.getElementById("url-embed-block-template");
  const node = template.content.firstElementChild.cloneNode(true);

  const inputWrap  = node.querySelector(".url-embed-input-wrap");
  const input      = node.querySelector(".url-embed-input");
  const card       = node.querySelector(".url-embed-card");
  const titleEl    = node.querySelector(".url-embed-title");
  const descEl     = node.querySelector(".url-embed-description");
  const providerEl = node.querySelector(".url-embed-provider");
  const logoEl     = node.querySelector(".url-embed-logo");
  const editBtn    = node.querySelector(".url-embed-edit-btn");
  const errorWrap  = node.querySelector(".url-embed-error");
  const errorMsg   = node.querySelector(".url-embed-error-msg");
  const retryBtn   = node.querySelector(".url-embed-retry-btn");

  // 상태 렌더링 ─────────────────────────────────────────────────────────────

  function showInputMode() {
    input.value = block.url || "";
    inputWrap.hidden = false;
    card.hidden      = true;
    errorWrap.hidden = true;
    input.focus();
  }

  function showCard() {
    titleEl.textContent    = block.title       || block.url || "제목 없음";
    descEl.textContent     = block.description || "";
    providerEl.textContent = block.provider    || "";
    card.href              = block.url;

    if (block.logo) {
      logoEl.src = block.logo;
      logoEl.hidden = false;
    } else {
      logoEl.hidden = true;
    }

    descEl.hidden  = !block.description;
    card.hidden    = false;
    inputWrap.hidden = true;
    errorWrap.hidden = true;
  }

  function showError(msg) {
    errorMsg.textContent = msg || "메타데이터를 가져올 수 없습니다.";
    input.value = block.url || "";
    inputWrap.hidden = false;
    card.hidden      = true;
    errorWrap.hidden = false;
  }

  function setLoading(isLoading) {
    input.disabled = isLoading;
    input.placeholder = isLoading ? "가져오는 중..." : "URL을 붙여넣으세요...";
  }

  // 초기 렌더링 ─────────────────────────────────────────────────────────────

  if (block.status === "success" && block.url) {
    showCard();
  } else if (block.status === "error") {
    showError(null);
  } else {
    showInputMode();
  }

  // URL fetch 처리 ──────────────────────────────────────────────────────────

  async function fetchMeta(url) {
    if (!url) return;
    setLoading(true);
    try {
      const meta = await apiFetchUrlEmbed(url, block.id);
      // block 객체를 업데이트해서 카드/에러 렌더링에 반영
      Object.assign(block, meta);
      if (meta.status === "success") {
        showCard();
      } else {
        showError(meta.error);
      }
    } catch (err) {
      showError("서버 오류가 발생했습니다.");
      console.error("URL embed fetch 실패:", err);
    } finally {
      setLoading(false);
    }
  }

  // 이벤트 ──────────────────────────────────────────────────────────────────

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      const url = input.value.trim();
      if (url) fetchMeta(url);
    }
    if (e.key === "Escape") {
      // 이미 성공 상태가 있으면 카드로 되돌아감
      if (block.status === "success" && block.url) showCard();
    }
  });

  // 카드 표시 중 편집 버튼 → URL 재입력 모드
  editBtn.addEventListener("click", (e) => {
    e.preventDefault();  // <a> 클릭 전파 차단
    e.stopPropagation();
    showInputMode();
  });

  // 에러 상태에서 재시도
  retryBtn.addEventListener("click", () => {
    const url = input.value.trim() || block.url;
    if (url) fetchMeta(url);
  });

  // 로고 로드 실패 시 숨김
  logoEl.addEventListener("error", () => { logoEl.hidden = true; });

  return node;
}
