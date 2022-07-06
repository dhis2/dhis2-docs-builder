// Get the modal
var modal = document.getElementById("simpleModal");

// Get the button that opens the modal
var btn = document.getElementById("simpleBtn");

// Get the <span> element that closes the modal
var span = document.getElementsByClassName("simpleClose")[0];

// When the user clicks the button, open the modal
btn.onclick = function() {
  var res = ssGetWithExpiry('ssPhrase');
  if (res != null){
    document.getElementById("simplesearch").value = res;
    document.getElementById("simplematches").innerHTML = ssGetWithExpiry('ssMatches');
  }
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

function ssSetWithExpiry(key, value, ttl) {
	const now = new Date()
    
	// `item` is an object which contains the original value
	// as well as the time when it's supposed to expire
	const item = {
		value: value,
		expiry: now.getTime() + ttl,
	}
	localStorage.setItem(key, JSON.stringify(item))
}

function ssGetWithExpiry(key) {
	const itemStr = localStorage.getItem(key)
	// if the item doesn't exist, return null
	if (!itemStr) {
		return null
	}
	const item = JSON.parse(itemStr)
	const now = new Date()
    
	// compare the expiry time of the item with the current time
	if (now.getTime() > item.expiry) {
        
		// If the item is expired, delete the item from storage
		// and return null
		localStorage.removeItem(key)
		return null
	}
	return item.value
}

// Variable to hold the locations
var dataArr = {};
var langbase = String(document.currentScript.src).replace('resources/javascript/simple_search.js','');

// Load the locations once, on page-load.
$(document).ready(function() {

    var localData = ssGetWithExpiry('ssIndex');
    if (localData != null){
        window.dataArr = localData;
    }
    else {
        $.ajax({
            cache: true,
            success: function(data) {
                
                ssSetWithExpiry('ssIndex',data,3600000);
                window.dataArr = data;
            },
            url: langbase + 'search/search_index_simple.json'

        });
    }
});
// Respond to any input change, and show first few matches
$("#simplesearch").on('input', function() {

    var searchphrase = $(this).val().toLowerCase().replace('"','\"');
    var di = document.getElementById("simpleInfo");


    if (searchphrase.length < 4){ 
        $('#simplematches').html('');
        ssSetWithExpiry('ssMatches','',86400000);
    }
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

            var res = '<div class="card"><a href="' + langbase + m.location + '"><div class="container"><p class="sectitle">' + m.title + '</p><p class="sectext">' + highlighter(m.text, searchphrase, true) + '</p></div></a></div>';

            var tabCell = tr.insertCell(-1);
            tabCell.innerHTML = res;

        }
        di.innerHTML = " matches: "+ ms.length;
        var divContainer = document.getElementById("simplematches");
        divContainer.innerHTML = "";
        divContainer.appendChild(results);
        ssSetWithExpiry('ssMatches',divContainer.innerHTML,86400000);
        //$('#matches').html(ms.join('\n'));
    }
    ssSetWithExpiry('ssPhrase',$(this).val(),86400000);

});

        function highlighter(text, phrase, cropStart = false) {
            //text = escapeHtml(text);
            var start = text.toLowerCase().indexOf(phrase);
            var first = 0;
            if (cropStart) first = start-100;
            if (start == -1) return escapeHtml(text.substring(0,100-phrase.length));
            else {
                return escapeHtml(text.substring(first,start))+'<mark>'+ escapeHtml(text.substring(start,start+phrase.length))+'</mark>'+ highlighter(text.substring(start+phrase.length),phrase);   // The function returns the product of p1 and p2
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
