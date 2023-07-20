{% load i18n %}
{% load static %}
function updateDialer(data){
    var iframe = document.getElementById("hl-widget-frame");
    iframe.contentWindow.postMessage(data, '*');
    if ($(".chat_container").is(":hidden")) {
        $(".c_h .right_c .mini").text("-")
        $(".chat_container").slideToggle("slow");
    }

}

(function(global){
    global.$_HelpLine_ClientId  ='{{ client_id }}';
    global.$_HelpLine_WidgetId='12bcejb';
    global.$_HelpLine_Unstable=false;
    global.$_HelpLine = global.$_HelpLine || {};

    var link = document.createElement( "link" );
    link.href = "https://{{ request.get_host }}{% static 'helpline/css/embed.css' %}";
    link.type = "text/css";
    link.rel = "stylesheet";
    link.media = "screen,print";
    document.getElementsByTagName( "head" )[0].appendChild( link );

    (function (w){
        function l() {
            if (window.$_HelpLine.init !== undefined) {
                return;
            }

            window.$_HelpLine.init = true;

            var files = [
                'https://{{ request.get_host }}{% static "jquery/dist/jquery.min.js" %}',
                'https://{{ request.get_host }}{% static "howler.js/dist/howler.min.js" %}',
            ];

            var s0=document.getElementsByTagName('script')[0];

            for (var i = 0; i < files.length; i++) {
                var s1 = document.createElement('script');
                s1.src= files[i];
                s1.charset='UTF-8';
                s1.setAttribute('crossorigin','*');
                s0.parentNode.insertBefore(s1,s0);
            }


            var dialer_container = document.createElement('div');
            dialer_container.innerHTML = `

                <div class="l_c_h">
                <div class="c_h">
                <div class="left_c">
                <div class="left right_c left_icons">
                <a href="#" class="mini" style="font-size:23px;">+</a>
                </div>
                <div class="left center_icons"><!--center_icons-->
                Dialer
                </div><!--end center_icons-->
                </div>
                <div class="right right_c" style="width:35px;">
                <a href="#" class="logout" title="End chat" name="" style="display:none;">
                <img src="" alt="End">
                </a>
                </div>
                <div class="clear"></div>
                </div>
                <div class="chat_container" style="display: none;">
                <div id="helpline-container">

                </div>

                <p class="footer_c">
                Powered by <a href="https://callcenter.africa/" target="_blank">Call Center Africa</a>
                </p>
                </div>
                </div>
                `;

            document.body.appendChild(dialer_container);

            (function(window, document, version, callback) {
                var j, d;
                var loaded = false;
                if (!(j = window.jQuery) || version > j.fn.jquery || callback(j, loaded)) {
                    // Widget code here

                    var script = document.createElement("script");
                    script.type = "text/javascript";
                    script.src = "https://{{ request.get_host }}{% static 'jquery/dist/jquery.min.js' %}";
                    script.onload = script.onreadystatechange = function() {
                        if (!loaded && (!(d = this.readyState) || d == "loaded" || d == "complete")) {
                            callback((j = window.jQuery).noConflict(1), loaded = true);
                            j(script).remove();
                        }
                    };
                    (document.getElementsByTagName("head")[0] || document.documentElement).appendChild(script);
                }

            })(window, document, "1.3", function($, jquery_loaded) {
                // Widget code here
                $(function(){
                    $(".c_h").click(function(e) {
                        if ($(".chat_container").is(":visible")) {
                            $(".c_h .right_c .mini").text("+")
                        } else {
                            $(".c_h .right_c .mini").text("-")
                        }
                        $(".chat_container").slideToggle("slow");
                        return false
                    });
                });
            });

            hl_container = document.getElementById("helpline-container");
            hl_container.innerHTML = `<iframe sandbox="allow-same-origin allow-scripts allow-forms allow-popups" allow="autoplay; microphone" src="https://{{ request.get_host }}/helpline/embeddable/?response_type=code&amp;redirect_uri={{ redirect_uris }}&amp;client_id={{ client_id }}" id="hl-widget-frame" frameBorder="0" height="250px">
        </iframe>`;


        }
        if (document.readyState === 'complete') {
            l();
        } else if (w.attachEvent) {
            w.attachEvent('onload', l);
        } else {
            w.addEventListener('load', l, false);
        }
    })(window);

})(window);
