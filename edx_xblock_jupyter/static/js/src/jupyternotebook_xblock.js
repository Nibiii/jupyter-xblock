/* Javascript for JupyterXBlock. */
function JupyterNotebookXBlock(runtime, element) {
  // run api call that returns a set-cookie
 $(document).ready(function() {
    $.ajax({
    type: "POST",
    url: sifu_url,
    crossDomain: true,
    xhrFields: {
      withCredentials: true
    },
    beforeSend: function(xhr, settings){
      xhr.setRequestHeader("Authorization", 'Bearer ' + sifu_token);
    },
    success: function(xhr, data){
    }
    });
  });

}
