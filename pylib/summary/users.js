const users = document.querySelector('#users button');

if (users) {
  function toggleUsers(event) {
    const div = document.querySelector('#users .users-container');
    div.classList.toggle('expanded');
    event.target.classList.toggle('expanded');
  }

  users.addEventListener('click', toggleUsers);
}
