$(document).ready(function() {
    $('#settings').click(function() {
        $.ajax({
            url: '/settings',
            success: function(data) {
                $('#content').html(data);
            }
        });
    });
});
