function getCSRFToken() {
    const match = document.cookie.match(/csrftoken=([\w-]+)/);
    return match ? match[1] : '';
}

function toggleTask(taskId) {
    fetch(`/tasks/toggle/${taskId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCSRFToken(),
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Request failed');
        }
        return response.json();
    })
    .then(data => {
        const statusCell = document.getElementById(`status-${taskId}`);

        if (!statusCell) {
            console.error(`Element status-${taskId} not found`);
            return;
        }

        if (data.status === 'completed') {
            statusCell.innerHTML = '<span class="badge bg-success">Completed</span>';
        } else {
            statusCell.innerHTML = '<span class="badge bg-warning text-dark">Pending</span>';
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const buttons = document.querySelectorAll('.toggle-btn');

    buttons.forEach(button => {
        button.addEventListener('click', function () {
            const taskId = this.dataset.id;
            toggleTask(taskId);
        });
    });
});