document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    const input = document.getElementById("phone");
    input.value = chip.dataset.phone;
    input.focus();
  });
});
