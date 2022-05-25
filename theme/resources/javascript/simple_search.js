// Get the modal
var modal = document.getElementById("simpleModal");

// Get the button that opens the modal
var btn = document.getElementById("simpleBtn");

// Get the <span> element that closes the modal
var span = document.getElementsByClassName("simpleClose")[0];

// When the user clicks the button, open the modal
btn.onclick = function() {
  modal.style.display = "block";
}

// When the user clicks on <span> (x), close the modal
span.onclick = function() {
  modal.style.display = "none";
}

// When the user clicks anywhere outside of the modal, close it
window.onclick = function(event) {
  if (event.target == modal) {
    modal.style.display = "none";
  }
}




// Variable to hold the locations
var dataArr = {};
// Load the locations once, on page-load.
$(document).ready(function() {
    $.getJSON( "/search/search_index_simple.json").done(function(data) {
        window.dataArr = data;
    }).fail(function(data) {
        console.log('no results found');
        //window.dataArr = testData; // remove this line in non-demo mode
    });
});
// Respond to any input change, and show first few matches
$("#simplesearch").on('input', function() {

    var searchphrase = $(this).val().toLowerCase();
    var di = document.getElementById("simpleInfo");


    if (searchphrase.length < 4){ $('#simplematches').html('')}
    else{
        di.innerHTML = "searching...";
        // find the current version
        var vv = window.location.href.match(/dhis-core-version-[^/]+/);
        var searchV = "";
        var ms;
        if (vv) {
            searchV = vv[0].replace('dhis-core-version-','DHIS core version ').replace(' 2',' 2.');

            ms = dataArr.filter(function(place) {
                // look for the entry with a matching `code` value
                return (place.text.toLowerCase().indexOf(searchphrase) !== -1 && (place.versions.length === 0 || place.versions.includes(searchV)));
            }); // create one text with a line per matched title
        }
        else {
            ms = dataArr.filter(function(place) {
                // look for the entry with a matching `code` value
                return (place.text.toLowerCase().indexOf(searchphrase) !== -1 );
            }); // create one text with a line per matched title
        }

        var results = document.createElement("table");
        lastpage = '';
        for (let i = 0; i < ms.length; i++) {
            var m = ms[i];
            //console.log(m);
            var page = m.location.substring(0,m.location.indexOf('#'));
            if (page != lastpage){
                var tr = results.insertRow(-1);

                var tabCell = tr.insertCell(-1);
                tabCell.className = "pagetitle";
                tabCell.colSpan = 2;
                tabCell.innerHTML = page.replace(/\/([^/]*$)/, '/<span class="bread">$1</span>') ;
            }
            lastpage = page;
            var tr = results.insertRow(-1);

            var res = '<div class="card"><a href="' + m.location + '"><div class="container"><p class="sectitle">' + m.title + '</p><p class="sectext">' + highlighter(m.text, searchphrase, true) + '</p></div></a></div>';

            var tabCell = tr.insertCell(-1);
            tabCell.innerHTML = res;

        }
        di.innerHTML = " matches: "+ ms.length;
        var divContainer = document.getElementById("simplematches");
        divContainer.innerHTML = "";
        divContainer.appendChild(results);
        //$('#matches').html(ms.join('\n'));
    }

});

        function highlighter(text, phrase, cropStart = false) {
            //text = escapeHtml(text);
            var start = text.toLowerCase().indexOf(phrase);
            var first = 0;
            if (cropStart) first = start-100;
            if (start == -1) return text.substring(0,100-phrase.length);
            else {
                return text.substring(first,start)+'<mark>'+ escapeHtml(text.substring(start,start+phrase.length))+'</mark>'+ highlighter(text.substring(start+phrase.length),phrase);   // The function returns the product of p1 and p2
            }

        function escapeHtml(unsafe)
        {
            return unsafe
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;")
                    .replace(/"/g, "&quot;")
                    .replace(/'/g, "&#039;");
            }
    }
