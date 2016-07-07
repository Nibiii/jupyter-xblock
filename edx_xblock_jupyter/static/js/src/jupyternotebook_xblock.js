/* Javascript for JupyterhubXBlock. */
function JupyterhubXBlock(runtime, element) {
  // run api call that returns a set-cookie
  $(document).ready(function() {
    $.ajax({
    type: "POST",
    url: cookie_api_url,
    crossDomain: true,
    xhrFields: {
      withCredentials: true
    },
    beforeSend: function(xhr, settings){
        xhr.setRequestHeader("Authorization", auth_token);
    },
    success: function(xhr, data){
      alert("YAY");
    }
    });
  });

}
