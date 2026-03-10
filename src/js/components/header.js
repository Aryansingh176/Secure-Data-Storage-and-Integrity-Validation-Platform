const header = document.createElement('header');
header.classList.add('header');

const logo = document.createElement('div');
logo.classList.add('logo');
logo.textContent = 'Data Integrity Platform';

const nav = document.createElement('nav');
const navList = document.createElement('ul');

const pages = ['Dashboard', 'Data Sources', 'Validation Rules', 'Reports', 'Settings'];

pages.forEach(page => {
    const navItem = document.createElement('li');
    const navLink = document.createElement('a');
    navLink.href = `${page.toLowerCase().replace(' ', '-')}.html`;
    navLink.textContent = page;
    navItem.appendChild(navLink);
    navList.appendChild(navItem);
});

nav.appendChild(navList);
header.appendChild(logo);
header.appendChild(nav);

document.body.insertBefore(header, document.body.firstChild);