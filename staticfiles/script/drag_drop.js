const dragStart = (event) => {
  event.dataTransfer.setData("text/plain", event.target.id);
}

const allowDrop = (event) => {
  event.preventDefault();
}

const drop = (event) => {
  event.preventDefault();
  const data = event.dataTransfer.getData("text/plain");
  const element = document.querySelector(`#${data}`);
  try {
    event.target.appendChild(element);
  } catch (error) {
    console.warn("you can't move the item to the same place")
  }
}