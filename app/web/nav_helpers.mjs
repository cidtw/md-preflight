export function bindWordmarkHome(wordmark, onHome) {
  if (!wordmark) {
    return;
  }
  wordmark.addEventListener("click", onHome);
}
