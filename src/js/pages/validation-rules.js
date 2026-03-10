// This file contains JavaScript specific to the validation rules page, handling rule management.

document.addEventListener('DOMContentLoaded', function() {
    const ruleForm = document.getElementById('validation-rule-form');
    const ruleList = document.getElementById('rule-list');

    ruleForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const ruleInput = document.getElementById('rule-input').value;
        if (ruleInput) {
            addRule(ruleInput);
            ruleForm.reset();
        }
    });

    function addRule(rule) {
        const listItem = document.createElement('li');
        listItem.textContent = rule;
        ruleList.appendChild(listItem);
    }
});