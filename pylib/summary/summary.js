const users = document.querySelector('#users button');
const allFilters = {{filters | safe}};
const pageSize = {{ pageSize }};
const allGroups = {{ groups | safe }};
const tbody = document.querySelector('#reconciliation tbody');

let hidden = {};
let maxPage = 0;

const toggleUsers = (event) => {
    const div = document.querySelector('#users .users-container');
    div.classList.toggle('expanded');
    event.target.classList.toggle('expanded');
}

// Toggle a group of rows open/closed. That is we will show/hide all records
// for a group. Closing them leaves only the first record (the reconciled one)
// visible.
const toggleHide = (event) => {
    if (!event.target.matches('button')) { return; }
    event.target.classList.toggle('hide');
    const groupBy = event.target.dataset.groupBy;
    const selector = '#reconciliation tbody tr[data-group-by="' + groupBy + '"]';
    const trs = document.querySelectorAll(selector);
    trs.forEach((r) => { r.classList.toggle('hide'); });
    hidden[groupBy] = event.target.classList.contains('hide');
}

// Like the toggleClosed function (above) but it's for all groups of records.
const toggleHideAll = (event) => {
    event.target.classList.toggle('hide');
    const trs = document.querySelectorAll('#reconciliation tbody tr.sub');
    const btn = document.querySelectorAll('#reconciliation tbody button');
    if (event.target.classList.contains('hide')) {
        trs.forEach(r => { r.classList.add('hide'); });
        btn.forEach(b => { b.classList.add('hide'); });
    } else {
        trs.forEach(r => { r.classList.remove('hide'); });
        btn.forEach(b => { b.classList.remove('hide'); });
    }
    Object.keys(hidden).forEach(k => hidden[k] = event.target.classList.contains('hide'));
}

const getPage = () => {
    const pager = document.querySelector('#reconciliation .pager');
    let page = +pager.value;
    page = page < 1 ? 1 : page;
    page = page > maxPage ? maxPage : page;
    pager.value = page;
    return page;
}

const changePage = () => {
    const page = getPage();
    const filter = document.querySelector('#reconciliation .filter').value;
    const keys = allFilters[filter].slice((page - 1) * pageSize, page * pageSize);
    const groups = keys.map(k => allGroups[k]);
    tbody.innerHTML = groups.join('');

    keys.forEach(k => {
        const rows = document.querySelectorAll('#reconciliation tr[data-group-by="' + k + '"]');
        const btn = document.querySelector('button[data-group-by="' + k + '"]');
        console.log(hidden[k])
        if (hidden[k]) {
            rows.forEach(r => { r.classList.add('hide'); });
            btn.classList.add('hide');
        } else {
            rows.forEach(r => { r.classList.remove('hide'); });
            btn.classList.remove('hide');
        }
    });
}

const changeFilter = () => {
    const filter = document.querySelector('#reconciliation .filter').value;
    const pager = document.querySelector('#reconciliation .pager');
    maxPage = Math.ceil(allFilters[filter].length / pageSize);
    document.querySelector('#reconciliation .pager').setAttribute('max', maxPage);
    document.querySelector('#reconciliation .max-page').innerHTML = 'of ' + maxPage;
    pager.value = 1;
    changePage();
}

users.addEventListener('click', toggleUsers);

document.querySelector('#reconciliation tbody')
    .addEventListener('click', toggleHide);

document.querySelector('#reconciliation thead button')
    .addEventListener('click', toggleHideAll);

document.querySelector('#reconciliation .pager')
    .addEventListener('change', changePage);

document.querySelector('#reconciliation .filter')
    .addEventListener('change', changeFilter);

document.querySelector('#reconciliation .first-page')
    .addEventListener('click', () => {
        const pager = document.querySelector('#reconciliation .pager');
        pager.value = 1;
        changePage();
});

document.querySelector('#reconciliation .previous-page')
    .addEventListener('click', () => {
        const pager = document.querySelector('#reconciliation .pager');
        pager.value = +pager.value - 1;
        changePage();
});

document.querySelector('#reconciliation .next-page')
    .addEventListener('click', () => {
        const pager = document.querySelector('#reconciliation .pager');
        pager.value = +pager.value + 1;
        changePage();
});

document.querySelector('#reconciliation .last-page')
    .addEventListener('click', () => {
        const pager = document.querySelector('#reconciliation .pager');
        pager.value = maxPage;
        changePage();
});

window.addEventListener('load', (event) => {
    Object.keys(allGroups).forEach(k => { hidden[k] = true; });

    changeFilter();
});