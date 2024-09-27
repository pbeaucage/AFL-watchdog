let timelineInstance = null;
let timelineData = null;
let groupsData = null;

function parseDate(dateString) {
    try {
        const [date, time] = dateString.split(' ');
        let [month, day, year] = date.split('/');
        const [hours, minutes, secondsMs] = time.split('-')[0].split(':');
        
        if (year.length === 2) {
            year = '20' + year;
        }
        
        return new Date(year, month - 1, day, hours, minutes, secondsMs.split('.')[0]);
    } catch (error) {
        console.error('Error parsing date:', dateString, error);
        return null;
    }
}

function prettyPrintJSON(obj) {
    const replacer = (key, value) => {
        if (typeof value === 'string') {
            return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }
        return value;
    };
    const formatted = JSON.stringify(obj, replacer, 2);
    return formatted.replace(/\n/g, '<br>').replace(/\s{2}/g, '&nbsp;&nbsp;');
}

function createTimelineData(data, offsets = {}) {
    const items = [];
    const groups = [];

    let groupId = 0;
    for (const [serverName, serverData] of Object.entries(data)) {
        if (serverData.queue && serverData.queue.length > 0) {
            groups.push({ id: groupId, content: serverName });

            const offset = (offsets[serverName] || 0) * 60 * 1000; // Convert minutes to milliseconds

            for (const queue of serverData.queue) {
                for (const task of queue) {
                    if (task.meta && task.meta.started && task.meta.ended) {
                        const start = parseDate(task.meta.started);
                        const end = parseDate(task.meta.ended);
                        if (start && end) {
                            items.push({
                                id: items.length,
                                group: groupId,
                                content: task.task.task_name,
                                start: new Date(start.getTime() + offset),
                                end: new Date(end.getTime() + offset),
                                title: `<div class="tooltip-content">${prettyPrintJSON(task.task)}</div>`
                            });
                        }
                    }
                }
            }

            groupId++;
        }
    }

    return { items, groups };
}


function setCookie(name, value, days) {
    const expires = new Date();
    expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
    document.cookie = name + '=' + JSON.stringify(value) + ';expires=' + expires.toUTCString() + ';path=/';
}

function getCookie(name) {
    const nameEQ = name + "=";
    const ca = document.cookie.split(';');
    for(let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) === 0) return JSON.parse(c.substring(nameEQ.length, c.length));
    }
    return null;
}

function initTimeline(data) {
    timelineData = data;
    const savedOffsets = getCookie('serverOffsets') || {};
    const { items, groups } = createTimelineData(data, savedOffsets);
    groupsData = groups;

    if (items.length === 0) {
        document.getElementById('timeline').innerHTML = 'No valid data to display';
        return;
    }

    const startDates = items.map(item => item.start);
    const endDates = items.map(item => item.end);
    const minDate = new Date(Math.min(...startDates));
    const maxDate = new Date(Math.max(...endDates));

    const container = document.getElementById('timeline');
    const options = {
        stack: false,
        start: minDate,
        end: maxDate,
        zoomMin: 1000 * 60 * 60,
        zoomMax: 1000 * 60 * 60 * 24 * 30,
        tooltip: {
            followMouse: true,
            overflowMethod: 'cap',
            delay: 300
        }
    };

    timelineInstance = new vis.Timeline(container, items, groups, options);

    // Create offset inputs
    const controlsDiv = document.getElementById('controls');
    groups.forEach(group => {
        const input = document.createElement('div');
        input.className = 'offset-input';
        input.innerHTML = `
            <label for="offset-${group.id}">${group.content} Offset (min):</label>
            <input type="number" id="offset-${group.id}" value="${savedOffsets[group.content] || 0}">
        `;
        controlsDiv.insertBefore(input, document.getElementById('redrawButton'));
    });
}
function redrawTimeline() {
    if (!timelineInstance || !timelineData || !groupsData) return;

    const offsets = {};
    document.querySelectorAll('.offset-input input').forEach(input => {
        const groupId = parseInt(input.id.split('-')[1]);
        const serverName = groupsData.find(group => group.id === groupId).content;
        offsets[serverName] = parseInt(input.value) || 0;
    });

    // Store offsets in cookie
    setCookie('serverOffsets', offsets, 30); // Store for 30 days

    const { items, groups } = createTimelineData(timelineData, offsets);
    timelineInstance.setItems(items);
}

document.addEventListener('DOMContentLoaded', function() {
    fetch('status.json')
        .then(response => response.json())
        .then(data => {
            initTimeline(data);
            document.getElementById('redrawButton').addEventListener('click', redrawTimeline);
        })
        .catch(error => {
            console.error('Error loading or parsing the JSON file:', error);
            document.getElementById('timeline').innerHTML = 'Error loading data';
        });
});
