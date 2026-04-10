function getCSRFToken() {
    const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? match[1] : '';
}

function toggleTask(taskId, eventObj) {
    fetch(`/tasks/toggle/${taskId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCSRFToken(),
            'Content-Type': 'application/json'
        },
        credentials: 'same-origin'
    })
    .then(res => res.json())
    .then(data => {
        if (!data || !data.status) return;

        if (data.status === 'completed') {
            eventObj.setProp('color', 'green');
        } else {
            eventObj.setProp('color', 'orange');
        }
    })
    .catch(err => console.error('Toggle error:', err));
}

document.addEventListener('DOMContentLoaded', function () {
    const calendarEl = document.getElementById('calendar');

    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        height: 650,
        events: events,

        eventClick: function(info) {
            const taskId = info.event.id;
            toggleTask(taskId, info.event);
        }
    });

    calendar.render();
});