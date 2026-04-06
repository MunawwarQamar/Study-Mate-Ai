function toggleTask(taskId) {
    fetch(`/tasks/toggle/${taskId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.cookie.match(/csrftoken=([\w-]+)/)[1],
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        const statusCell = document.getElementById(`status-${taskId}`);
        if (data.status === 'completed') {
            statusCell.innerHTML = '<span class="badge bg-success">Completed</span>';
        } else {
            statusCell.innerHTML = '<span class="badge bg-warning text-dark">Pending</span>';
        }
    });
}