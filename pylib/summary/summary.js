const users = document.querySelector('#users button');

function toggleUsers(event) {
    const div = document.querySelector('#users .users-container');
    div.classList.toggle('expanded');
    event.target.classList.toggle('expanded');
}

users.addEventListener('click', toggleUsers);

// Toggle a group of rows open/closed. That is we will show/hide all records
// for a group. Closing them leaves only the first record (the reconciled one)
// visible.
const toggleHide = function (event) {
    if (!event.target.matches('button')) { return; }
    const groupBy = event.target.dataset.groupBy;
    const selector = '#reconciliation tbody tr[data-group-by="' + groupBy + '"]';
    const trs = document.querySelectorAll(selector);
    trs.forEach(function (r) { r.classList.toggle('hide'); });
}

// Like the toggleClosed function (above) but it's for all groups of records.
const toggleAllHide = function (event) {
    event.target.classList.toggle('hide');
    const trs = document.querySelectorAll('#reconciliation tbody tr.sub');
    if (event.target.classList.contains('hide')) {
        trs.forEach(function (r) { r.classList.add('hide'); });
    } else {
        trs.forEach(function (r) { r.classList.remove('hide'); });
    }
}


document.querySelector('#reconciliation tbody')
    .addEventListener('click', toggleHide);

document.querySelector('#reconciliation thead button')
    .addEventListener('click', toggleAllHide);


var maxPage = 0;

const changePage = function () {
    const pager = document.querySelector('#reconciliation .pager');
    const filter = document.querySelector('#reconciliation .filter').value;
    var page = +pager.value;
    page = page < 1 ? 1 : page;
    page = page > maxPage ? maxPage : page;
    pager.value = page;
    const data = rowData(page, filter);
    buildPage(data);
}

const filterChange = function () {
    const filter = document.querySelector('#reconciliation .filter').value;
    maxPage = Math.ceil(filters[filter].length / args.page_size);
    document.querySelector('#reconciliation .pager').setAttribute('max', maxPage);
    document.querySelector('#reconciliation .max-page').innerHTML = 'of ' + maxPage;
    changePage();
}

document.querySelector('#reconciliation .pager')
    .addEventListener('change', changePage);
document.querySelector('#reconciliation .filter')
    .addEventListener('change', filterChange);

document.querySelector('#reconciliation .first-page')
    .addEventListener('click', function () {
        const pager = document.querySelector('#reconciliation .pager');
        pager.value = 1;
        changePage();
    });

document.querySelector('#reconciliation .previous-page')
    .addEventListener('click', function () {
        const pager = document.querySelector('#reconciliation .pager');
        pager.value = +pager.value - 1;
        changePage();
    });

document.querySelector('#reconciliation .next-page')
    .addEventListener('click', function () {
        const pager = document.querySelector('#reconciliation .pager');
        pager.value = +pager.value + 1;
        changePage();
    });

document.querySelector('#reconciliation .last-page')
    .addEventListener('click', function () {
        const pager = document.querySelector('#reconciliation .pager');
        pager.value = maxPage;
        changePage();
    });

filterChange();
