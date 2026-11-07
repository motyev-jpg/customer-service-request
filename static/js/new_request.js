const categories = JSON.parse(document.getElementById("categories-data").textContent);
const lang = JSON.parse(document.getElementById("lang-data").textContent);
const categorySelect = document.getElementById("category");
const subSelect = document.getElementById("subcategory");

function fillSubcategories(selected) {
  const placeholder = subSelect.dataset.placeholder;
  subSelect.replaceChildren(new Option(placeholder, ""));
  const category = categories.find((c) => c.id === categorySelect.value);
  if (!category) return;
  category.subcategories.forEach((s) => {
    subSelect.add(new Option(s[lang], s.id, false, s.id === selected));
  });
}

categorySelect.addEventListener("change", () => fillSubcategories(""));
fillSubcategories(subSelect.dataset.selected);
