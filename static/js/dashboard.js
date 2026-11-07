document.querySelectorAll("tr.clickable").forEach((row) => {
  row.addEventListener("click", (event) => {
    if (event.target.closest("a")) return;
    window.location.href = row.dataset.href;
  });
});
