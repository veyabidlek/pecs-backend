const tabItems = Array.from(document.querySelectorAll('.tab'))
const contentItems = Array.from(document.querySelectorAll('.board-container'))

const clearActiveClass = (element, className = 'active') => {
  console.log("Element");
  element.find(item => item.classList.remove(`${ className }`))
}

const setActiveClass = (element, index, className = 'active') => {
    console.log("Index", index);
    console.log("Element", element);
  element[index].classList.add(`${ className }`)
}

const checkoutTabs = (item, index) => {
  item.addEventListener('click', () => {
    console.log("Item", item)
    if (item.classList.contains('active')) return
    console.log(item)

    clearActiveClass(tabItems)
    clearActiveClass(contentItems)

    setActiveClass(tabItems, index)
    setActiveClass(contentItems, index)
  })
}

tabItems.forEach(checkoutTabs)