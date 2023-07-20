const defaultDomain = 'callcenter.africa';

var configOptions = {
    defaultDomain           : defaultDomain,
    enrollmentDomain        : defaultDomain,
    hotDesks        : [],
    publicUrl               : 'https://callcenter.africa',
    janusServer                : 'https://webrtc-gateway.callcenter.africa/janus',
    incomingRingToneAudioFile                : '/static/helpline/audio/incoming.webm',
};

// Server URL should always be HTTTPS
server = configOptions.janusServer;

var janus = null;
var sipcall = null;
var opaqueId = "siptest-"+Janus.randomString(12);

var spinner = null;

var selectedApproach = "secret";
var registered = false;
var masterId = null, helpers = {}, helpersCount = 0;

var incoming = null;
var ringenabled = true;

var incomingAudio =  new Howl({
    src: [configOptions.incomingRingToneAudioFile],
    loop: true
});

function registerSIPdetails(data) {
	var sipserver = data.sip_proxy;
	var username = data.sip_username;
	var password = data.sip_secret;
    var demo_mode = data.demo;

    if (data.webrtc_gateway_url) {
        janus_server = data.webrtc_gateway_url;
    } else {
        janus_server = configOptions.janusServer;
    }
	var register = {
		request: "register",
		username: username
	};

    // Check if we're in demo mode
    if (demo_mode){
        toastr.info(
            "You are currently in DEMO Mode. Contact your administrator for assistance.",
            "DEMO MODE",
            {
                "closeButton": false,
                "debug": false,
                "newestOnTop": false,
                "progressBar": true,
                "positionClass": "toast-top-right",
                "preventDuplicates": false,
                "onclick": null,
                "showDuration": "300",
                "hideDuration": "1000",
                "timeOut": "5000",
                "extendedTimeOut": "1000",
                "showEasing": "swing",
                "hideEasing": "linear",
                "showMethod": "fadeIn",
                "hideMethod": "fadeOut"
            }
        );
    }

    $('#username').val(username);
    $('#sip_domain').val(data.sip_proxy);
	// By default, the SIP plugin tries to extract the username part from the SIP
	// identity to register; if the username is different, you can provide it here
	var authuser = data.sip_authuser.toString();
	if(authuser !== "") {
		register.authuser = authuser;
	}
	// The display name is only needed when you want a friendly name to appear when you call someone
	var displayname = data.sip_displayname;
	if(displayname !== "") {
		register.display_name = displayname;
	}
    // Use the plain secret
    register["secret"] = password;
	// Should you want the SIP stack to add some custom headers to the
	// REGISTER, you can do so by adding an additional "headers" object,
	// containing each of the headers as key-value, e.g.:
	//		register["headers"] = {
	//			"My-Header": "value",
	//			"AnotherHeader": "another string"
	//		};
	// Similarly, a "contact_params" object will allow you to
	// inject custom Contact URI params, e.g.:
	//		register["contact_params"] = {
	//			"pn-provider": "acme",
	//			"pn-param": "acme-param",
	//			"pn-prid": "ZTY4ZDJlMzODE1NmUgKi0K"
	//		};
    register["proxy"] = data.sip_proxy;
    // Uncomment this if you want to see an outbound proxy too
    //~ register["outbound_proxy"] = "sip:outbound.example.com";

	Janus.init({debug: "all", callback: function() {
		// Start the SIP stack
			// Make sure the browser supports WebRTC
			if(!Janus.isWebrtcSupported()) {
				bootbox.alert("No WebRTC support... ");
				return;
			}
			// Create session
			janus = new Janus(
                {
					server: janus_server,
					success: function() {
						// Attach to SIP plugin
						janus.attach(
							{
								plugin: "janus.plugin.sip",
								opaqueId: opaqueId,
								success: function(pluginHandle) {
									sipcall = pluginHandle;
                                    // Register to helpline
                                    sipcall.send({ message: register });
                                    console.log(register);

									Janus.log("Plugin attached! (" + sipcall.getPlugin() + ", id=" + sipcall.getId() + ")");
									// Prepare the username registration
									//$('#register').click(registerUsername);
                                    //janus.destroy();
								},
								error: function(error) {
									Janus.error("  -- Error attaching plugin...", error);
									bootbox.alert("  -- Error attaching plugin... " + error);
								},
								consentDialog: function(on) {
									Janus.debug("Consent dialog should be " + (on ? "on" : "off") + " now");
									if(on) {
										// Darken screen and show hint
										$.blockUI({
											message: '<div><img src="/static/helpline/images/up_arrow.png"/></div>',
											css: {
												border: 'none',
												padding: '15px',
												backgroundColor: 'transparent',
												color: '#aaa',
												top: '10px',
												left: (navigator.mozGetUserMedia ? '-100px' : '300px')
											} });
									} else {
										// Restore screen
										$.unblockUI();
									}
								},
								iceState: function(state) {
									Janus.log("ICE state changed to " + state);
								},
								mediaState: function(medium, on) {
									Janus.log("Janus " + (on ? "started" : "stopped") + " receiving our " + medium);
								},
								webrtcState: function(on) {
									Janus.log("Janus says our WebRTC PeerConnection is " + (on ? "up" : "down") + " now");
								},
								slowLink: function(on) {
                                    $('#phone-status').removeClass("bg-green");
                                    $('#phone-status').addClass("bg-yellow");
								},
								onmessage: function(msg, jsep) {
									Janus.debug(" ::: Got a message :::", msg);
									// Any error?
									var error = msg["error"];
									if(error) {
										if(!registered) {
                                            Janus.log(error)
										} else {
											// Reset status
											sipcall.hangup();
										}
										bootbox.alert(error);
										return;
									}
									var callId = msg["call_id"];
									var result = msg["result"];
									if(result && result["event"]) {
										var event = result["event"];
										if(event === 'registration_failed') {
											Janus.warn("Registration failed: " + result["code"] + " " + result["reason"]);
											bootbox.alert(result["code"] + " " + result["reason"]);
											return;
										}
										if(event === 'registered') {
											Janus.log("Successfully registered as " + result["username"] + "!");
											$('#you').removeClass('hide').show().text(result["username"]);
                                            localStorage.userName = result["username"];
											$('#id_softphone').val(result["username"]);
                                            $("#phone-status").removeClass("fa-plug");
                                            $("#phone-status").addClass("fa-signal");
                                            $('#phone-status').addClass("bg-green");
                                            // Update queue data on successful registration
                                            getDataQueues();
											// TODO Enable buttons to call now
											if(!registered) {
												registered = true;
												masterId = result["master_id"];
												$('#phone_tools').append(
													'<button id="addhelper" class="btn btn-round-big btn-info" title="Add a new line">' +
														'<i class="fa fa-plus"></i>' +
													'</button>'
												);
												$('#addhelper').click(addHelper);
												$('#phone').removeClass('hide').show();
												$('#call').unbind('click').click(doCall);
											}
										} else if(event === 'calling') {
											Janus.log("Waiting for the peer to answer...");
											// TODO Any ringtone?
											$('#call').removeAttr('disabled').html('<i class="fa fa-phone rotate-135"></i>')
												  .removeClass("btn-success").addClass("btn-danger")
												  .unbind('click').click(doHangup);
                                            $('#call-buttons').removeClass("hide");
                                            $('#phone-status').removeClass("bg-yellow");
										} else if(event === 'incomingcall') {
                                            playBeep();
                                            if (ringenabled) {
                                                incomingAudio.play();
                                            }
                                            console.log("Result is ",  result);
                                            caller_uri = parseUri(result["username"]);
                                            caller_name = result["displayname"];
											showNotification("Incoming Call", "Incoming call from " + caller_name + " " +  caller_uri.user + "!");

											Janus.log("Incoming call from " + caller_name + " " + result["username"] + "!");
											sipcall.callId = callId;
											var doAudio = true, doVideo = true;
											var offerlessInvite = false;
											if(jsep) {
												// What has been negotiated?
												doAudio = (jsep.sdp.indexOf("m=audio ") > -1);
												doVideo = (jsep.sdp.indexOf("m=video ") > -1);
												Janus.debug("Audio " + (doAudio ? "has" : "has NOT") + " been negotiated");
												Janus.debug("Video " + (doVideo ? "has" : "has NOT") + " been negotiated");
											} else {
												Janus.log("This call doesn't contain an offer... we'll need to provide one ourselves");
												offerlessInvite = true;
												// In case you want to offer video when reacting to an offerless call, set this to true
												doVideo = false;
											}
											// Is this the result of a transfer?
											var transfer = "";
											var referredBy = result["referred_by"];
											if(referredBy) {
												transfer = " (referred by " + referredBy + ")";
												transfer = transfer.replace(new RegExp('<', 'g'), '&lt');
												transfer = transfer.replace(new RegExp('>', 'g'), '&gt');
											}
											// Any security offered? A missing "srtp" attribute means plain RTP
											var rtpType = "";
											var srtp = result["srtp"];
											if(srtp === "sdes_optional")
												rtpType = " (SDES-SRTP offered)";
											else if(srtp === "sdes_mandatory")
												rtpType = " (SDES-SRTP mandatory)";
											// Notify user
											bootbox.hideAll();
											var extra = "";
                                            caller_uri = parseUri(result["username"]);
                                            caller_name = result["displayname"];
											if(offerlessInvite)
												extra = " (no SDP offer provided)"
                                            if($('#toggle_auto_answer_btn').html() === "On")
                                            {
                                                // Auto Answer the call
                                                console.log("Auto Answer Call!!");
                                                incoming = null;
                                                $('#peer').val(result["username"]).attr('disabled', true);
                                                $( ".btn-digit" ).addClass( "btn-dtmf" );
                                                // Notice that we can only answer if we got an offer: if this was
                                                // an offerless call, we'll need to create an offer ourselves
                                                var sipcallAction = (offerlessInvite ? sipcall.createOffer : sipcall.createAnswer);
                                                sipcallAction(
                                                    {
                                                        jsep: jsep,
                                                        media: { audio: doAudio, video: doVideo },
                                                        success: function(jsep) {
                                                            Janus.debug("Got SDP " + jsep.type + "! audio=" + doAudio + ", video=" + doVideo + ":", jsep);
                                                            var body = { request: "accept" };
                                                            sipcall.send({ message: body, jsep: jsep });
                                                            $('#call').removeAttr('disabled').html('<i class="fa fa-phone rotate-135"></i>')
                                                                .removeClass("btn-success").addClass("btn-danger")
                                                                .unbind('click').click(doHangup);
                                                            $('#call-buttons').removeClass("hide");
                                                            $('#phone-status').removeClass("bg-yellow");
                                                            stopTimer();
                                                        },
                                                        error: function(error) {
                                                            Janus.error("WebRTC error:", error);
                                                            bootbox.alert("WebRTC error... " + error.message);
                                                            // Don't keep the caller waiting any longer, but use a 480 instead of the default 486 to clarify the cause
                                                            var body = { request: "decline", code: 480 };
                                                            sipcall.send({ message: body });
                                                        }
                                                    });
                                            } else {
                                                window.postMessage(caller_uri.user, "*");
                                                incoming = bootbox.dialog({
                                                    message: "Incoming call from " + caller_name + " " + caller_uri.user + "!" + transfer + rtpType + extra,
                                                    closeButton: true,
                                                    backdrop: true,
                                                    onEscape: function() {incomingAudio.stop();},
                                                    title: "Incoming call",
                                                    buttons: {
                                                        success: {
                                                            label: "Answer",
                                                            className: "btn-success",
                                                            callback: function() {
                                                                incoming = null;
                                                                $('#peer').val(caller_name+" "+result["username"]).attr('disabled', true);
                                                                $( ".btn-digit" ).addClass( "btn-dtmf" );
                                                                // Notice that we can only answer if we got an offer: if this was
                                                                // an offerless call, we'll need to create an offer ourselves
                                                                var sipcallAction = (offerlessInvite ? sipcall.createOffer : sipcall.createAnswer);
                                                                sipcallAction(
                                                                    {
                                                                        jsep: jsep,
                                                                        media: { audio: doAudio, video: doVideo },
                                                                        success: function(jsep) {
                                                                            Janus.debug("Got SDP " + jsep.type + "! audio=" + doAudio + ", video=" + doVideo + ":", jsep);
                                                                            var body = { request: "accept" };
                                                                            sipcall.send({ message: body, jsep: jsep });
                                                                            $('#call').removeAttr('disabled').html('<i class="fa fa-phone rotate-135"></i>')
                                                                                .removeClass("btn-success").addClass("btn-danger")
                                                                                .unbind('click').click(doHangup);
                                                                            $('#call-buttons').removeClass("hide");
                                                                            $('#phone-status').removeClass("bg-yellow");
                                                                            stopTimer();
                                                                        },
                                                                        error: function(error) {
                                                                            Janus.error("WebRTC error:", error);
                                                                            bootbox.alert("WebRTC error... " + error.message);
                                                                            // Don't keep the caller waiting any longer, but use a 480 instead of the default 486 to clarify the cause
                                                                            var body = { request: "decline", code: 480 };
                                                                            sipcall.send({ message: body });
                                                                        }
                                                                    });
                                                            }
                                                        },
                                                        danger: {
                                                            label: "Decline",
                                                            className: "btn-danger",
                                                            callback: function() {
                                                                incoming = null;
                                                                var body = { request: "decline" };
                                                                sipcall.send({ message: body });
                                                            }
                                                        }
                                                    }
                                                });
                                            }
										} else if(event === 'accepting') {
											// Response to an offerless INVITE, let's wait for an 'accepted'
										} else if(event === 'progress') {
											Janus.log("There's early media from " + result["username"] + ", wairing for the call!", jsep);
											// Call can start already: handle the remote answer
											if(jsep) {
												sipcall.handleRemoteJsep({ jsep: jsep, error: doHangup });
											}
											toastr.info("Early media...");
										} else if(event === 'accepted') {
											Janus.log(result["username"] + " accepted the call!", jsep);
											// Call can start, now: handle the remote answer
											if(jsep) {
												sipcall.handleRemoteJsep({ jsep: jsep, error: doHangup });
											}
											toastr.success("Call accepted!");
                                            $('#call-buttons').removeClass("hide");
                                            $('#phone-status').removeClass("bg-yellow");
                                            startTimer();
                                            incomingAudio.stop();
											sipcall.callId = callId;
                                            // Check if case is assigned to the current user
                                            // The is specific to Helpline application
                                            // CTI Integration for CRM Popup
                                            setTimeout(check_call,2000); // run check_call after 2 seconds
                                            setTimeout(check_call,4000); // run check_call again after 4 seconds

										} else if(event === 'updatingcall') {
											// We got a re-INVITE: while we may prompt the user (e.g.,
											// to notify about media changes), to keep things simple
											// we just accept the update and send an answer right away
											Janus.log("Got re-INVITE");
											var doAudio = (jsep.sdp.indexOf("m=audio ") > -1),
												doVideo = (jsep.sdp.indexOf("m=video ") > -1);
											sipcall.createAnswer(
												{
													jsep: jsep,
													media: { audio: doAudio, video: doVideo },
													success: function(jsep) {
														Janus.debug("Got SDP " + jsep.type + "! audio=" + doAudio + ", video=" + doVideo + ":", jsep);
														var body = { request: "update" };
														sipcall.send({ message: body, jsep: jsep });
													},
													error: function(error) {
														Janus.error("WebRTC error:", error);
														bootbox.alert("WebRTC error... " + error.message);
													}
												});
										} else if(event === 'message') {
											// We got a MESSAGE
											var sender = result["displayname"] ? result["displayname"] : result["sender"];
											var content = result["content"];
											content = content.replace(new RegExp('<', 'g'), '&lt');
											content = content.replace(new RegExp('>', 'g'), '&gt');
											toastr.success(content, "Message from " + sender);
										} else if(event === 'info') {
											// We got an INFO
											var sender = result["displayname"] ? result["displayname"] : result["sender"];
											var content = result["content"];
											content = content.replace(new RegExp('<', 'g'), '&lt');
											content = content.replace(new RegExp('>', 'g'), '&gt');
											toastr.info(content, "Info from " + sender);
										} else if(event === 'notify') {
											// We got a NOTIFY
											var notify = result["notify"];
											var content = result["content"];
											toastr.info(content, "Notify (" + notify + ")");
										} else if(event === 'transfer') {
											// We're being asked to transfer the call, ask the user what to do
											var referTo = result["refer_to"];
											var referredBy = result["referred_by"] ? result["referred_by"] : "an unknown party";
											var referId = result["refer_id"];
											var replaces = result["replaces"];
											var extra = ("referred by " + referredBy);
											if(replaces)
												extra += (", replaces call-ID " + replaces);
											extra = extra.replace(new RegExp('<', 'g'), '&lt');
											extra = extra.replace(new RegExp('>', 'g'), '&gt');
											bootbox.confirm("Transfer the call to " + referTo + "? (" + extra + ")",
												function(result) {
													if(result) {
														// Call the person we're being transferred to
														if(!sipcall.webrtcStuff.pc) {
															// Do it here
															$('#peer').val(referTo).attr('disabled', true);
															actuallyDoCall(sipcall, referTo, false, referId);
                                                             $( ".btn-digit" ).addClass( "btn-dtmf" );
														} else {
															// We're in a call already, use a helper
															var h = -1;
															if(Object.keys(helpers).length > 0) {
																// See if any of the helpers if available
																for(var i in helpers) {
																	if(!helpers[i].sipcall.webrtcStuff.pc) {
																		h = parseInt(i);
																		break;
																	}
																}
															}
															if(h !== -1) {
																// Do in this helper
																$('#peer' + h).val(referTo).attr('disabled', true);
                                                                 $( ".btn-digit" ).addClass( "btn-dtmf" );
																actuallyDoCall(helpers[h].sipcall, referTo, false, referId);
															} else {
																// Create a new helper
																addHelper(function(id) {
																	// Do it here
																	$('#peer' + id).val(referTo).attr('disabled', true);
																	actuallyDoCall(helpers[id].sipcall, referTo, false, referId);
																});
															}
														}
													} else {
														// We're rejecting the transfer
														var body = { request: "decline", refer_id: referId };
														sipcall.send({ message: body });
													}
												});
										} else if(event === 'hangup') {
											if(incoming != null) {
												incoming.modal('hide');
												incoming = null;
											}
											Janus.log("Call hung up (" + result["code"] + " " + result["reason"] + ")!");

                                            // Play hangup sounds
                                            playBeep();
                                            //playHangupSound();
											toastr.info(result["code"] + " " + result["reason"]);
											// Reset status
											sipcall.hangup();
											$('#dovideo').removeAttr('disabled').val('');
											$('#peer').removeAttr('disabled').val('');
                                            $( ".btn-digit" ).removeClass( "btn-dtmf" );
											$('#call').removeAttr('disabled').html('<i class="fa fa-phone"></i>')
												.removeClass("btn-danger").addClass("btn-success")
												.unbind('click').click(doCall);
                                            $('#call-buttons').addClass("hide");
                                            $('#phone-status').removeClass("bg-yellow");
                                            $('#phone-status').addClass("bg-green");
                                            stopTimer();
                                            incomingAudio.stop();
										}
									}
								},
								onlocalstream: function(stream) {
									Janus.debug(" ::: Got a local stream :::", stream);
									$('#videos').removeClass('hide').show();
									if($('#myvideo').length === 0)
										$('#videoleft').append('<video class="rounded centered" id="myvideo" width=320 height=240 autoplay playsinline muted="muted"/>');
									Janus.attachMediaStream($('#myvideo').get(0), stream);
									$("#myvideo").get(0).muted = "muted";
									if(sipcall.webrtcStuff.pc.iceConnectionState !== "completed" &&
											sipcall.webrtcStuff.pc.iceConnectionState !== "connected") {
										$("#videoleft").parent().block({
											message: '<b>Calling...</b>',
											css: {
												border: 'none',
												backgroundColor: 'transparent',
												color: 'white'
											}
										});
										// No remote video yet
										$('#videoright').append('<video class="rounded centered" id="waitingvideo" width=320 height=240 />');
										if(spinner == null) {
											var target = document.getElementById('videoright');
											spinner = new Spinner({top:100}).spin(target);
										} else {
											spinner.spin();
										}
									}
									var videoTracks = stream.getVideoTracks();
									if(!videoTracks || videoTracks.length === 0) {
										// No webcam
										$('#myvideo').hide();
										if($('#videoleft .no-video-container').length === 0) {
											$('#videoleft').append(
												'<div class="no-video-container">' +
													'<i class="fa fa-video-camera fa-5 no-video-icon"></i>' +
													'<span class="no-video-text">No webcam available</span>' +
												'</div>');
										}
									} else {
										$('#videoleft .no-video-container').remove();
										$('#myvideo').removeClass('hide').show();
									}
								},
								onremotestream: function(stream) {
									Janus.debug(" ::: Got a remote stream :::", stream);
									if($('#remotevideo').length === 0) {
										$('#videoright').parent().find('h3').html(
											'Send DTMF: <span id="dtmf" class="btn-group btn-group-xs"></span>' +
											'<span id="ctrls" class="pull-right btn-group btn-group-xs">' +
												'<button id="msg" title="Send message" class="btn btn-info"><i class="fa fa-envelope"></i></button>' +
												'<button id="info" title="Send INFO" class="btn btn-info"><i class="fa fa-info"></i></button>' +
												'<button id="transfer" title="Transfer call" class="btn btn-info"><i class="fa fa-mail-forward"></i></button>' +
											'</span>');
										$('#videoright').append(
											'<video class="rounded centered hide" id="remotevideo" width=320 height=240 autoplay playsinline/>');
										for(var i=0; i<12; i++) {
											if(i<10)
												$('#dtmf').append('<button class="btn btn-info dtmf">' + i + '</button>');
											else if(i == 10)
												$('#dtmf').append('<button class="btn btn-info dtmf">#</button>');
											else if(i == 11)
												$('#dtmf').append('<button class="btn btn-info dtmf">*</button>');
										}
										$('.btn-dtmf').click(function() {
											// Send DTMF tone (inband)
											sipcall.dtmf({dtmf: { tones: $(this).text()}});
											// Notice you can also send DTMF tones using SIP INFO
											// 		sipcall.send({ message: { request: "dtmf_info", digit: $(this).text() }});
										});
										$('#msg').click(function() {
											bootbox.prompt("Insert message to send", function(result) {
												if(result && result !== '') {
													// Send the message
													var msg = { request: "message", content: result };
													sipcall.send({ message: msg });
												}
											});
										});
										$('#info').click(function() {
											bootbox.dialog({
												message: 'Type: <input class="form-control" type="text" id="type" placeholder="e.g., application/xml">' +
													'<br/>Content: <input class="form-control" type="text" id="content" placeholder="e.g., <message>hi</message>">',
												title: "Insert the type and content to send",
												buttons: {
													cancel: {
														label: "Cancel",
														className: "btn-default",
														callback: function() {
															// Do nothing
														}
													},
													ok: {
														label: "OK",
														className: "btn-primary",
														callback: function() {
															// Send the INFO
															var type = $('#type').val();
															var content = $('#content').val();
															if(type === '' || content === '')
																return;
															var msg = { request: "info", type: type, content: content };
															sipcall.send({ message: msg });
														}
													}
												}
											});
										});

                                        // Microphone Mute Unmute
                                        audioenabled = true;
                                        $('#toggleaudio').unbind('click').bind('click',
                                            function() {

                                                audioenabled = !audioenabled;
                                                if(audioenabled){
                                                    $('#toggleaudio').html('<i class="fa fa-microphone text-success"></i>');
                                                    sipcall.unmuteAudio();

                                                } else {
                                                    $('#toggleaudio').html('<i class="fa fa-microphone-slash text-danger"></i>');
                                                    sipcall.muteAudio();


                                                }
                                            });


										$('#transfer').unbind('click').bind('click', function() {
                                            var active_calls = [];
                                            for ( const property in helpers ) {if(helpers[property].sipcall.callId) {active_calls.push({text: "Line " + property, value: helpers[property].sipcall.callId }) }};
											if (active_calls === undefined || active_calls.length == 0) {
												toastr.info("You have to be on more than one call for attended transfer");
												return;
											}

											bootbox.prompt({
												message: 'Select an active line to transfer to',
												title: "Attended transfer",
                                                inputType: 'radio',
                                                inputOptions: active_calls,
                                                callback: function(result) {
                                                    // Start an attended transfer
                                                    var address = $('#transferto').val();
                                                    if(address === '')
                                                        return;
                                                    address = "sip:" + address + "@zerxis.com";
                                                    // Add the call-id to replace to the transfer
                                                    var msg = { request: "transfer", uri: address, replace: result};
                                                    sipcall.send({ message: msg });
                                                }
                                            });
										});

                                        // Put caller on Hold
                                        callheld = false;
										$('#togglehold*').unbind('click').bind('click',
                                            function() {
                                                callheld = !callheld;
                                                if(callheld){
                                                    let body = {"request" : "hold", "direction": "inactive"}
                                                    sipcall.send({ message: body });
                                                    $('#togglehold').html('<i class="fa fa-play-circle-o"></i>');
                                                    toastr.info("Hold ");
                                                    console.log("callheld is " + callheld);
                                                } else {
                                                    let body = {"request" : "unhold"}
                                                    // Toggle hold on other helpers

                                                    let helper_body = {"request" : "hold", "direction": "inactive"}
                                                    if(Object.keys(helpers).length > 0) {
                                                        // See if any of the helpers if available
                                                        for(var i in helpers) {
                                                            helpers[i].sipcall.send({ message: helper_body });
                                                            $('#togglehold' + i).html('<i class="fa fa-play-circle-o"></i>');
                                                            // toastr.info("Line " + i + " Hold");
                                                        }
                                                    }

                                                    sipcall.send({ message: body});
                                                    toastr.info("Unhold");
                                                    console.log("callheld is " + callheld);
                                                    $('#togglehold').html('<i class="fa fa-pause-circle-o"></i>');
                                                }

										});


										// Show the peer and hide the spinner when we get a playing event
										$("#remotevideo").bind("playing", function () {
											$('#waitingvideo').remove();
											if(this.videoWidth)
												$('#remotevideo').removeClass('hide').show();
											if(spinner)
												spinner.stop();
											spinner = null;
										});
									}
									Janus.attachMediaStream($('#remotevideo').get(0), stream);
									var videoTracks = stream.getVideoTracks();
									if(!videoTracks || videoTracks.length === 0) {
										// No remote video
										$('#remotevideo').hide();
										if($('#videoright .no-video-container').length === 0) {
											$('#videoright').append(
												'<div class="no-video-container">' +
													'<i class="fa fa-video-camera fa-5 no-video-icon"></i>' +
													'<span class="no-video-text">No remote video available</span>' +
												'</div>');
										}
									} else {
										$('#videoright .no-video-container').remove();
										$('#remotevideo').removeClass('hide').show();
									}
								},
								oncleanup: function() {
									Janus.log(" ::: Got a cleanup notification :::");
									$('#myvideo').remove();
									$('#waitingvideo').remove();
									$('#remotevideo').remove();
									$('#videos .no-video-container').remove();
									$('#videos').hide();
									$('#dtmf').parent().html("Remote UA");
									if(sipcall)
										sipcall.callId = null;
								}
							});
					},
					error: function(error) {
						Janus.error(error);
                        // Show toastr error and try to auto-reconnect
                        // Set a random connect interval
                        // For now you're stuck with what you get
                        toastr.error(error);
                        $('#phone-status').removeClass("fa-signal");
                        $('#connection_message').removeClass("hidden");
                        $('#phone-status').addClass("fa-exclamation-triangle");
                        $('#phone-status').removeClass("bg-green");
                        let reconnect_trials = 0;
                        let reconnect_max_trial = 2;

                        // Select a random interval to try and reconnect
                        let reconnect_interval = Math.floor(Math.random() * 10000) + 2000;
                        console.log("Reconnect interval " + reconnect_interval);
                        console.log("Reconnect trial " + reconnect_trials + " of " + reconnect_max_trial);
                        startReconnectTimer(reconnect_interval/1000);
						var try_reconnect = setInterval(function() {
                            reconnect_trials++;
                            if (reconnect_trials > reconnect_max_trial) {
                                bootbox.alert("Could not connect to server, reloading page.");
                                reconnect_trials = 0;
                                location.reload();
                            }

                            console.log("Trying to reconnect after " + reconnect_interval);
                            startReconnectTimer(reconnect_interval/1000);

							janus.reconnect({
								success: function() {
									console.log("Session successfully reclaimed:", janus.getSessionId());
                                    toastr.success("Reconnected!");
                                    clearInterval(try_reconnect);
                                    $('#phone-status').removeClass("fa-exclamation-triangle");
                                    $('#phone-status').addClass("fa-signal");
                                    $('#phone-status').addClass("bg-green");
                                    $('#connection_message').addClass("hidden");
                                    stopReconnectTimer();
								},
								error: function(err) {
									console.error("Failed to reconnect:", err);
									// Might have an exponential backoff, here, or simply fail
								}
							});
						}, reconnect_interval);

					},
					destroyed: function() {
						window.location.reload();
					}
				});
	}});
}


function makePrimary(sip_authuser){
    $('ul#hotdesk_list').html('');
    configOptions.hotDesks.forEach(function (value, i) {
        console.log('%d: %s', i, value.sip_authuser);
        if (value.sip_authuser === sip_authuser){
            $('#you').text(value.sip_authuser);
            registerSIPdetails(value);
            configOptions.defaultDomain = value.sip_domain;
            configOptions.sipProxy = value.sip_proxy;

            var values = {
                'sip_authuser': value.sip_authuser,
            }
            $.ajax({
                url: "/helpline/ajax/hotdesk_makeprimary/",
                type: "GET",
                data: values,
                success: function(data) {
                    if (!(data['success'])) {
                        // Register new primary
                        console.log("Could not make primary " + value.sip_authuser );
                    }
                    else {
                        console.log("New primary " + value.sip_authuser );
                        // PJAX wasnt' working here
                        document.getElementById('dashboard_home_link').click();
                        //$.pjax({url : "{% url "dashboard_home"  %}", container: '#pjax-container', timeout: 10000});


                    }
                },
                error: function () {
                    toastr.error("Could not make primary");
                }
            });

        } else {
            $('ul#hotdesk_list').append('<li><a href="#" onclick="makePrimary('+ value.sip_authuser +' );">' + value.sip_authuser + '@'+ value.sip_domain + '</a></li>');
        }
    });
};

function getSIPdetails(){
    // Get SIP details from Helpline Server
    console.log("Getting SIP details from Helpline Server");
    $.ajax({
        url : "/helpline/ajax/get_sip_details/",
        type : "GET",
        data : {},

        // handle a successful response
        success : function(data){
            configOptions.hotDesks = data.slice();
            primary_account = null;
            data.forEach(addHotdeskLink);
            function addHotdeskLink(value, index, array) {
                console.log(value.primary);
                if (value.primary){
                    primary_account = value;
                } else {
                    $('ul#hotdesk_list').append('<li><a href="#" onclick="makePrimary('+ value.sip_authuser +' );">' + value.sip_authuser + '@'+ value.sip_domain + '</a></li>');
                }
            }

            // Register primary account
            // If none register the first account returned
            if (primary_account){
                registerSIPdetails(primary_account);
            } else {
                primary_account = data.shift()
                registerSIPdetails(primary_account);
            }


            configOptions.defaultDomain = primary_account.sip_domain;
            configOptions.sipProxy = primary_account.sip_proxy;
        },

        //handle a non-successful response
        error: function(xhr,errmsg,err) {
            console.log(xhr.status + ": " + xhr.resposeText);
            return false;
        }
    });
};
           

$(document).ready(function() {
    var sip_details = getSIPdetails();

	// Initialize the library (all console debuggers enabled)
});

function checkEnter(field, event) {
	var theCode = event.keyCode ? event.keyCode : event.which ? event.which : event.charCode;
	if(theCode == 13) {
		if(field.id == 'server' || field.id == 'username')
			registerUsername();
		else if(field.id == 'peer')
			doCall();
		return false;
	} else {
		return true;
	}
}

function registerUsername(sipserver, username, authuser, displayname, password, register,) {
    var selectedApproach = "secret";
	if(!selectedApproach) {
		bootbox.alert("Please select a registration approach from the dropdown menu");
		return;
	}
	// Let's see if the user provided a server address
	// 		NOTE WELL! Even though the attribute we set in the request is called "proxy",
	//		this is actually the _registrar_. If you want to set an outbound proxy (for this
	//		REGISTER request and for all INVITEs that will follow), you'll need to set the
	//		"outbound_proxy" property in the request instead. The two are of course not
	//		mutually exclusive. If you set neither, the domain part of the user identity
	//		will be used as the target of the REGISTER request the plugin might send.
	var sipserver = server;
	if(sipserver !== "" && sipserver.indexOf("sip:") != 0 && sipserver.indexOf("sips:") !=0) {
		bootbox.alert("Please insert a valid SIP server (e.g., sip:192.168.0.1:5060)");
		return;
	}
	if(selectedApproach === "guest") {
		// We're registering as guests, no username/secret provided
		var register = {
			request: "register",
			type: "guest"
		};
		if(sipserver !== "") {
			register["proxy"] = sipserver;
			// Uncomment this if you want to see an outbound proxy too
			//~ register["outbound_proxy"] = "sip:outbound.example.com";
		}
		var username = $('#username').val();
		if(!username === "" || username.indexOf("sip:") != 0 || username.indexOf("@") < 0) {
			bootbox.alert("Please insert a valid SIP address (e.g., sip:goofy@example.com): this doesn't need to exist for guests, but is required");
			return;
		}
		register.username = username;
		var displayname = $('#displayname').val();
		if(displayname) {
			register.display_name = displayname;
		}
		if(sipserver === "") {
			bootbox.confirm("You didn't specify a SIP Registrar to use: this will cause the plugin to try and conduct a standard (<a href='https://tools.ietf.org/html/rfc3263' target='_blank'>RFC3263</a>) lookup. If this is not what you want or you don't know what this means, hit Cancel and provide a SIP Registrar instead'",
				function(result) {
					if(result) {
						// sipcall.send({ message: register });
					} else {
					}
				});
		} else {
			//sipcall.send({ message: register });
		}
		return;
	}
	var username = username;
	if(username === "" || username.indexOf("sip:") != 0 || username.indexOf("@") < 0) {
		bootbox.alert('Please insert a valid SIP identity address (e.g., sip:goofy@example.com)');
		return;
	}
	var password = password;
	if(password === "") {
		bootbox.alert("Insert the username secret (e.g., mypassword)");
		return;
	}
	var register = {
		request: "register",
		username: username
	};
	// By default, the SIP plugin tries to extract the username part from the SIP
	// identity to register; if the username is different, you can provide it here
	var authuser = authuser;
	if(authuser !== "") {
		register.authuser = authuser;
	}
	// The display name is only needed when you want a friendly name to appear when you call someone
	var displayname = $('#displayname').val();
	if(displayname !== "") {
		register.display_name = displayname;
	}
	if(selectedApproach === "secret") {
		// Use the plain secret
		register["secret"] = password;
	} else if(selectedApproach === "ha1secret") {
		var sip_user = username.substring(4, username.indexOf('@'));    /* skip sip: */
		var sip_domain = username.substring(username.indexOf('@')+1);
		register["ha1_secret"] = md5(sip_user+':'+sip_domain+':'+password);
	}
	// Should you want the SIP stack to add some custom headers to the
	// REGISTER, you can do so by adding an additional "headers" object,
	// containing each of the headers as key-value, e.g.:
	//		register["headers"] = {
	//			"My-Header": "value",
	//			"AnotherHeader": "another string"
	//		};
	// Similarly, a "contact_params" object will allow you to
	// inject custom Contact URI params, e.g.:
	//		register["contact_params"] = {
	//			"pn-provider": "acme",
	//			"pn-param": "acme-param",
	//			"pn-prid": "ZTY4ZDJlMzODE1NmUgKi0K"
	//		};
	if(sipserver === "") {
		bootbox.confirm("You didn't specify a SIP Registrar: this will cause the plugin to try and conduct a standard (<a href='https://tools.ietf.org/html/rfc3263' target='_blank'>RFC3263</a>) lookup. If this is not what you want or you don't know what this means, hit Cancel and provide a SIP Registrar instead'",
			function(result) {
				if(result) {
					//sipcall.send({ message: register });
				} else {
				}
			});
	} else {
		register["proxy"] = sipserver;
		// Uncomment this if you want to see an outbound proxy too
		//~ register["outbound_proxy"] = "sip:outbound.example.com";
		//sipcall.send({ message: register });
	}
}

function doCall(ev) {
	// Call someone (from the main session or one of the helpers)
	var button = ev ? ev.currentTarget.id : "call";
	var helperId = button.split("call")[1];
	if(helperId === "")
		helperId = null;
	else
		helperId = parseInt(helperId);
	var handle = helperId ? helpers[helperId].sipcall : sipcall;
	var prefix = helperId ? ("[Helper #" + helperId + "]") : "";
	var suffix = helperId ? (""+helperId) : "";
	$('#peer' + suffix).attr('disabled', true);
    $( ".btn-digit" ).addClass( "btn-dtmf" );
	$('#call' + suffix).attr('disabled', true).unbind('click');
	$('#dovideo' + suffix).attr('disabled', true);
	var username = $('#peer' + suffix).val().trim();
	if(username === "") {
		bootbox.alert('Please insert a valid SIP address (e.g., sip:pluto@example.com)');
		$('#peer' + suffix).removeAttr('disabled');
        $( ".btn-digit" ).removeClass( "btn-dtmf" );
		$('#dovideo' + suffix).removeAttr('disabled');
		$('#call' + suffix).removeAttr('disabled').click(function() { doCall(helperId); });
		return;
	}
    // Append default domain if username does not have a SIP domain
    if(username.indexOf("@") < 0){
        console.log("No domain defained..");
        if(configOptions.sipProxy.indexOf(":") < 0) {
            username += "@" + configOptions.defaultDomain;
            console.log("Calling using default domain" + username);
        } else {
            username += "@" + configOptions.sipProxy.slice(configOptions.sipProxy.indexOf(":")+1);
            console.log("Calling using username " + username);
        }

    }
    if(username.indexOf("sip:") !=0){
        username = "sip:" + username
    }

    console.log("Final string username " + username);

	if(username.indexOf("sip:") != 0 || username.indexOf("@") < 0) {
		bootbox.alert('Please insert a valid SIP address (e.g., sip:pluto@example.com)');
		$('#peer' + suffix).removeAttr('disabled').val("");
        $( ".btn-digit" ).removeClass( "btn-dtmf" );
		$('#dovideo' + suffix).removeAttr('disabled').val("");
		$('#call' + suffix).removeAttr('disabled').click(function() { doCall(helperId); });
		return;
	}
	// Call this URI
	doVideo = $('#dovideo' + suffix).is(':checked');
	Janus.log(prefix + "This is a SIP " + (doVideo ? "video" : "audio") + " call (dovideo=" + doVideo + ")");
    // Save Last called user name in localStorage for redial
    localStorage.lastCall = username;
    playBeep();
	actuallyDoCall(handle, username, doVideo);
}
function actuallyDoCall(handle, uri, doVideo, referId) {
	handle.createOffer(
		{
			media: {
				audioSend: true, audioRecv: true,		// We DO want audio
				videoSend: doVideo, videoRecv: doVideo	// We MAY want video
			},
			success: function(jsep) {
				Janus.debug("Got SDP!", jsep);
				// By default, you only pass the SIP URI to call as an
				// argument to a "call" request. Should you want the
				// SIP stack to add some custom headers to the INVITE,
				// you can do so by adding an additional "headers" object,
				// containing each of the headers as key-value, e.g.:
				//		var body = { request: "call", uri: $('#peer').val(),
				//			headers: {
				//				"My-Header": "value",
				//				"AnotherHeader": "another string"
				//			}
				//		};
				var body = { request: "call", uri: uri };
				// Note: you can also ask the plugin to negotiate SDES-SRTP, instead of the
				// default plain RTP, by adding a "srtp" attribute to the request. Valid
				// values are "sdes_optional" and "sdes_mandatory", e.g.:
				//		var body = { request: "call", uri: $('#peer').val(), srtp: "sdes_optional" };
				// "sdes_optional" will negotiate RTP/AVP and add a crypto line,
				// "sdes_mandatory" will set the protocol to RTP/SAVP instead.
				// Just beware that some endpoints will NOT accept an INVITE
				// with a crypto line in it if the protocol is not RTP/SAVP,
				// so if you want SDES use "sdes_optional" with care.
				// Note 2: by default, the SIP plugin auto-answers incoming
				// re-INVITEs, without involving the browser/client: this is
				// for backwards compatibility with older Janus clients that
				// may not be able to handle them. If you want to receive
				// re-INVITES to handle them yourself, specify it here, e.g.:
				//		body["autoaccept_reinvites"] = false;
				if(referId) {
					// In case we're originating this call because of a call
					// transfer, we need to provide the internal reference ID
					body["refer_id"] = referId;
				}
				handle.send({ message: body, jsep: jsep });
			},
			error: function(error) {
                let prefix = "";
				Janus.error(prefix + "WebRTC error...", error);
				bootbox.alert("WebRTC error... " + error.message);
			}
		});
}

function doHangup(ev) {
	// Hangup a call (on the main session or one of the helpers)
	var button = ev ? ev.currentTarget.id : "call";
	var helperId = button.split("call")[1];
    playBeep();
	if(helperId === "")
		helperId = null;
	else
		helperId = parseInt(helperId);
	if(!helperId) {
		$('#call').attr('disabled', true).unbind('click');
        $('#call-buttons').addClass("hide");
        $('#phone-status').removeClass("bg-yellow");
        $('#togglehold').html('<i class="fa fa-play-circle-o"></i>');
		var hangup = { request: "hangup" };
		sipcall.send({ message: hangup });
		sipcall.hangup();
	} else {
		$('#call' + helperId).attr('disabled', true).unbind('click');
        $('#call-buttons' + helperId).addClass("hide");
        $('#phone-status').removeClass("bg-yellow");
        $('#togglehold' + helperId).html('<i class="fa fa-play-circle-o"></i>');
		var hangup = { request: "hangup" };
		helpers[helperId].sipcall.send({ message: hangup });
		helpers[helperId].sipcall.hangup();
	}
}

// The following code is only needed if you're interested in supporting multiple
// calls at the same time. As explained in the Janus documentation, each Janus
// handle can only do one PeerConnection at a time, which means you normally
// cannot do multiple calls. If that's something you need (e.g., because you
// need to do a SIP transfer, or want to be in two calls), then the SIP plugin
// provides the so-called "helpers": basically additional handles attached to
// the SIP plugin, and associated to your SIP identity. They can be used to
// originate and receive calls exactly as the main handle: notice that incoming
// calls will be rejected with a "486 Busy" if you're in a call already and there
// are no available "helpers", which means you should add one in advance for that.
// In this demo, creating a "helper" adds a new row for calls that looks and
// works exactly as the default one: you can add more than one "helper", and
// obviously the more you have, the more concurrent calls you can have.
function addHelper(helperCreated) {
	helpersCount++;
	var helperId = helpersCount;
	helpers[helperId] = { id: helperId };
	// Add another row with a new "phone"
	$('.phone_footer').before(
		'<div class="col-md-12" id="sipcall' + helperId + '">' +
		'	<div class="">' +
		'		<div class="">' +
		'			<div class="">' +
		'				<span class="label label-info">Helper #' + helperId +
		'					<i class="fa fa-window-close" id="rmhelper' + helperId + '" style="cursor: pointer;" title="Remove this helper"></i>' +
		'				</span>' +
        '                   <button id="togglehold' + helperId + '" type="button" class="btn btn-round btn-default">' +
        '                       <i class="fa fa-pause-circle-o"></i>' +
        '                   </button>' +
		'			</div>' +
		'			<div class="col-md-6 container" id="phone' + helperId + '">' +
		'				<div class="input-group margin-bottom-sm">' +
		'					<input disabled class="form-control input-lg" type="text" placeholder="Number to call" autocomplete="off" id="peer' + helperId + '" onkeypress="return checkEnter(this, event, ' + helperId + ');"></input>' +
		'					<span class="input-group-addon"><button disabled class="btn btn-flat btn-xs" autocomplete="off" id="call' + helperId + '">Call</button></span>' +
		'				</div>' +
		'			<input autocomplete="off" id="dovideo' + helperId + '" type="checkbox" class="hide"><!-- Use Video --></input>' +
		'			</div>' +
		'		</div>' +
		'	<div/>' +
		'	<div id="videos' + helperId + '" class="hide">' +
		'		<div class="col-md-6">' +
		'			<div class="panel panel-default">' +
		'				<div class="panel-heading">' +
		'					<h3 class="panel-title">You</h3>' +
		'				</div>' +
		'				<div class="panel-body" id="videoleft' + helperId + '"></div>' +
		'			</div>' +
		'		</div>' +
		'		<div class="col-md-6">' +
		'			<div class="panel panel-default">' +
		'				<div class="panel-heading">' +
		'					<h3 class="panel-title">Remote UA</h3>' +
		'				</div>' +
		'				<div class="panel-body" id="videoright' + helperId + '"></div>' +
		'			</div>' +
		'		</div>' +
		'	</div>' +
		'</div>'
	);
	$('#rmhelper' + helperId).click(function() {
		var hid = $(this).attr('id').split("rmhelper")[1];
		console.log(hid);
		removeHelper(hid);
	});
	// Attach to SIP plugin, but only register as an helper for the master session
	janus.attach(
		{
			plugin: "janus.plugin.sip",
			opaqueId: opaqueId,
			success: function(pluginHandle) {
				helpers[helperId].sipcall = pluginHandle;
				Janus.log("[Helper #" + helperId + "] Plugin attached! (" + helpers[helperId].sipcall.getPlugin() + ", id=" + helpers[helperId].sipcall.getId() + ")");
				// TODO Send the "register"
				helpers[helperId].sipcall.send({
					message: {
						request: "register",
						type: "helper",
						username: $('#username').val(),	// We use the same username as the master session
						master_id: masterId				// Then we add the ID of the master session, nothing else
					}
				});
			},
			error: function(error) {
				Janus.error("[Helper #" + helperId + "]   -- Error attaching plugin...", error);
				bootbox.alert("  -- Error attaching plugin... " + error);
				removeHelper(helperId);
			},
			consentDialog: function(on) {
				Janus.debug("[Helper #" + helperId + "] Consent dialog should be " + (on ? "on" : "off") + " now");
				if(on) {
					// Darken screen and show hint
					$.blockUI({
						message: '<div><img src="/static/helpline/images/up_arrow.png"/></div>',
						css: {
							border: 'none',
							padding: '15px',
							backgroundColor: 'transparent',
							color: '#aaa',
							top: '10px',
							left: (navigator.mozGetUserMedia ? '-100px' : '300px')
						} });
				} else {
					// Restore screen
					$.unblockUI();
				}
			},
			iceState: function(state) {
				Janus.log("[Helper #" + helperId + "] ICE state changed to " + state);
			},
			mediaState: function(medium, on) {
				Janus.log("[Helper #" + helperId + "] Janus " + (on ? "started" : "stopped") + " receiving our " + medium);
			},
			webrtcState: function(on) {
				Janus.log("[Helper #" + helperId + "] Janus says our WebRTC PeerConnection is " + (on ? "up" : "down") + " now");
				$("#videoleft" + helperId).parent().unblock();
			},
			onmessage: function(msg, jsep) {
				Janus.debug("[Helper #" + helperId + "]  ::: Got a message :::", msg);
				// Any error?
				var error = msg["error"];
				if(error) {
					bootbox.alert(error);
					return;
				}
				var callId = msg["call_id"];
				var result = msg["result"];
				if(result && result["event"]) {
					var event = result["event"];
					if(event === 'registration_failed') {
						Janus.warn("[Helper #" + helperId + "] Registration failed: " + result["code"] + " " + result["reason"]);
						bootbox.alert(result["code"] + " " + result["reason"]);
						// Get rid of the helper
						removeHelper(helperId);
						return;
					}
					if(event === 'registered') {
						Janus.log("[Helper #" + helperId + "] Successfully registered as " + result["username"] + "!");
						// Unlock the "phone" controls
						$('#peer' + helperId).removeAttr('disabled');
                        $( ".btn-digit" ).removeClass( "btn-dtmf" );
						$('#call' + helperId).removeAttr('disabled').html('<i class="fa fa-phone"></i>')
							.removeClass("btn-danger").addClass("btn-success")
							.unbind('click').click(doCall);
                        $('#phone-status').removeClass("bg-yellow");
						if(helperCreated)
                            console.log("Helper created #" + helperId);
                            // TODO Execute after helper is created
                            //	helperCreated(helperId);

					} else if(event === 'calling') {
						Janus.log("[Helper #" + helperId + "] Waiting for the peer to answer...");
						// TODO Any ringtone?
						$('#call' + helperId).removeAttr('disabled').html('<i class="fa fa-phone"></i>')
							  .removeClass("btn-success").addClass("btn-danger")
							  .unbind('click').click(doHangup);
					} else if(event === 'incomingcall') {
                        playBeep();
						caller_uri = parseUri(result["username"]);
                        caller_name = result["displayname"];

						Janus.log("[Helper #" + helperId + "] Incoming call from "+ caller_name + " " + caller_uri.user + "! (on helper #" + helperId + ")");
						helpers[helperId].sipcall.callId = callId;
						var doAudio = true, doVideo = true;
						var offerlessInvite = false;
						showNotification("Incoming Call", "Incoming call from " + caller_name + " " + caller_uri.user + "!");
						if(jsep) {
							// What has been negotiated?
							doAudio = (jsep.sdp.indexOf("m=audio ") > -1);
							doVideo = (jsep.sdp.indexOf("m=video ") > -1);
							Janus.debug("[Helper #" + helperId + "] Audio " + (doAudio ? "has" : "has NOT") + " been negotiated");
							Janus.debug("[Helper #" + helperId + "] Video " + (doVideo ? "has" : "has NOT") + " been negotiated");
						} else {
							Janus.log("[Helper #" + helperId + "] This call doesn't contain an offer... we'll need to provide one ourselves");
							offerlessInvite = true;
							// In case you want to offer video when reacting to an offerless call, set this to true
							doVideo = false;
						}
						// Is this the result of a transfer?
						var transfer = "";
						var referredBy = result["referred_by"];
						var replaces = result["replaces"];
						if(referredBy && replaces)
							transfer = " (referred by " + referredBy + ", replaces call-ID " + replaces + ")";
						else if(referredBy && !replaces)
							transfer = " (referred by " + referredBy + ")";
						else if(!referredBy && replaces)
							transfer = " (replaces call-ID " + replaces + ")";
						transfer = transfer.replace(new RegExp('<', 'g'), '&lt');
						transfer = transfer.replace(new RegExp('>', 'g'), '&gt');
						// Any security offered? A missing "srtp" attribute means plain RTP
						var rtpType = "";
						var srtp = result["srtp"];
						if(srtp === "sdes_optional")
							rtpType = " (SDES-SRTP offered)";
						else if(srtp === "sdes_mandatory")
							rtpType = " (SDES-SRTP mandatory)";
						// Notify user
						bootbox.hideAll();
						var extra = "";
						caller_uri = parseUri(result["username"]);
                        caller_name = result["displayname"];
						if(offerlessInvite)
							extra = " (no SDP offer provided)"
						incoming = bootbox.dialog({
							message: "Incoming call from " + caller_name + " " + caller_uri.user + "!" + transfer + rtpType + extra + " (on helper #" + helperId + ")",
							title: "Incoming call " + caller_name + "(helper " + helperId + ")",
                            closeButton: true,
                            backdrop: true,
                            onEscape: function() {incomingAudio.stop();},
							buttons: {
								success: {
									label: "Answer",
									className: "btn-success",
									callback: function() {
										incoming = null;
										$('#peer' + helperId).val(result["username"]).attr('disabled', true);
										// Notice that we can only answer if we got an offer: if this was
										// an offerless call, we'll need to create an offer ourselves
										var sipcallAction = (offerlessInvite ? helpers[helperId].sipcall.createOffer : helpers[helperId].sipcall.createAnswer);
										sipcallAction(
											{
												jsep: jsep,
												media: { audio: doAudio, video: doVideo },
												success: function(jsep) {
													Janus.debug("[Helper #" + helperId + "] Got SDP " + jsep.type + "! audio=" + doAudio + ", video=" + doVideo + ":", jsep);
													var body = { request: "accept" };
													// Note: as with "call", you can add a "srtp" attribute to
													// negotiate/mandate SDES support for this incoming call.
													// The default behaviour is to automatically use it if
													// the caller negotiated it, but you may choose to require
													// SDES support by setting "srtp" to "sdes_mandatory", e.g.:
													//		var body = { request: "accept", srtp: "sdes_mandatory" };
													// This way you'll tell the plugin to accept the call, but ONLY
													// if SDES is available, and you don't want plain RTP. If it
													// is not available, you'll get an error (452) back. You can
													// also specify the SRTP profile to negotiate by setting the
													// "srtp_profile" property accordingly (the default if not
													// set in the request is "AES_CM_128_HMAC_SHA1_80")
													// Note 2: by default, the SIP plugin auto-answers incoming
													// re-INVITEs, without involving the browser/client: this is
													// for backwards compatibility with older Janus clients that
													// may not be able to handle them. If you want to receive
													// re-INVITES to handle them yourself, specify it here, e.g.:
													//		body["autoaccept_reinvites"] = false;
													helpers[helperId].sipcall.send({ message: body, jsep: jsep });
													$('#call' + helperId).removeAttr('disabled').html('<i class="fa fa-phone rotate-135"></i>')
														.removeClass("btn-success").addClass("btn-danger")
														.unbind('click').click(doHangup);
                                                    $('#call-buttons' + helperId).removeClass("hide");
                                                    $('#phone-status' + helperId).removeClass("bg-yellow");

												},
												error: function(error) {
													Janus.error("[Helper #" + helperId + "] WebRTC error:", error);
													bootbox.alert("WebRTC error... " + error.message);
													// Don't keep the caller waiting any longer, but use a 480 instead of the default 486 to clarify the cause
													var body = { request: "decline", code: 480 };
													helpers[helperId].sipcall.send({ message: body });
												}
											});
									}
								},
								danger: {
									label: "Decline",
									className: "btn-danger",
									callback: function() {
										incoming = null;
										var body = { request: "decline" };
										helpers[helperId].sipcall.send({ message: body });
									}
								}
							}
						});
					} else if(event === 'accepting') {
						// Response to an offerless INVITE, let's wait for an 'accepted'
					} else if(event === 'progress') {
						Janus.log("[Helper #" + helperId + "] There's early media from " + result["username"] + ", wairing for the call!", jsep);
						// Call can start already: handle the remote answer
						if(jsep) {
							helpers[helperId].sipcall.handleRemoteJsep({ jsep: jsep, error: function() {
								// Simulate an hangup from this helper's button
								doHangup({ currentTarget: { id: "call" + helperId } });
							}});
						}
						toastr.info("Early media...");
					} else if(event === 'accepted') {
						Janus.log("[Helper #" + helperId + "] " + result["username"] + " accepted the call!", jsep);
						// Call can start, now: handle the remote answer
						if(jsep) {
							helpers[helperId].sipcall.handleRemoteJsep({ jsep: jsep, error: function() {
								// Simulate an hangup from this helper's button
								doHangup({ currentTarget: { id: "call" + helperId } });
							}});
						}
						helpers[helperId].sipcall.callId = callId;
						toastr.success("Call accepted!");
					} else if(event === 'updatingcall') {
						// We got a re-INVITE: while we may prompt the user (e.g.,
						// to notify about media changes), to keep things simple
						// we just accept the update and send an answer right away
						Janus.log("[Helper #" + helperId + "] Got re-INVITE");
						var doAudio = (jsep.sdp.indexOf("m=audio ") > -1),
							doVideo = (jsep.sdp.indexOf("m=video ") > -1);
						helpers[helperId].sipcall.createAnswer(
							{
								jsep: jsep,
								media: { audio: doAudio, video: doVideo },
								success: function(jsep) {
									Janus.debug("[Helper #" + helperId + "] Got SDP " + jsep.type + "! audio=" + doAudio + ", video=" + doVideo + ":", jsep);
									var body = { request: "update" };
									helpers[helperId].sipcall.send({ message: body, jsep: jsep });
								},
								error: function(error) {
									Janus.error("[Helper #" + helperId + "] WebRTC error:", error);
									bootbox.alert("WebRTC error... " + error.message);
								}
							});
					} else if(event === 'message') {
						// We got a MESSAGE
						var sender = result["displayname"] ? result["displayname"] : result["sender"];
						var content = result["content"];
						content = content.replace(new RegExp('<', 'g'), '&lt');
						content = content.replace(new RegExp('>', 'g'), '&gt');
						toastr.success(content, "Message from " + sender);
					} else if(event === 'info') {
						// We got an INFO
						var sender = result["displayname"] ? result["displayname"] : result["sender"];
						var content = result["content"];
						content = content.replace(new RegExp('<', 'g'), '&lt');
						content = content.replace(new RegExp('>', 'g'), '&gt');
						toastr.info(content, "Info from " + sender);
					} else if(event === 'notify') {
						// We got a NOTIFY
						var notify = result["notify"];
						var content = result["content"];
						toastr.info(content, "Notify (" + notify + ")");
					} else if(event === 'transfer') {
						// We're being asked to transfer the call, ask the user what to do
						var referTo = result["refer_to"];
						var referredBy = result["referred_by"] ? result["referred_by"] : "an unknown party";
						var referId = result["refer_id"];
						var replaces = result["replaces"];
						var extra = ("referred by " + referredBy);
						if(replaces)
							extra += (", replaces call-ID " + replaces);
						extra = extra.replace(new RegExp('<', 'g'), '&lt');
						extra = extra.replace(new RegExp('>', 'g'), '&gt');
						bootbox.confirm("Transfer the call to " + referTo + "? (" + extra + ", helper " + helperId + ")",
							function(result) {
								if(result) {
									// Call the person we're being transferred to
									if(!helpers[helperId].sipcall.webrtcStuff.pc) {
										// Do it here
										$('#peer' + helperId).val(referTo).attr('disabled', true);
										actuallyDoCall(helpers[helperId].sipcall, referTo, false, referId);
									} else if(!sipcall.webrtcStuff.pc) {
										// Do it on the main handle
										$('#peer').val(referTo).attr('disabled', true);
										actuallyDoCall(sipcall, referTo, false, referId);
									} else {
										// We're in a call already, use the main handle or a helper
										var h = -1;
										if(Object.keys(helpers).length > 0) {
											// See if any of the helpers if available
											for(var i in helpers) {
												if(!helpers[i].sipcall.webrtcStuff.pc) {
													h = parseInt(i);
													break;
												}
											}
										}
										if(h !== -1) {
											// Do in this helper
											$('#peer' + h).val(referTo).attr('disabled', true);
											actuallyDoCall(helpers[h].sipcall, referTo, false, referId);
										} else {
											// Create a new helper
											addHelper(function(id) {
												// Do it here
												$('#peer' + id).val(referTo).attr('disabled', true);
												actuallyDoCall(helpers[id].sipcall, referTo, false, referId);
											});
										}
									}
								} else {
									// We're rejecting the transfer
									var body = { request: "decline", refer_id: referId };
									sipcall.send({ message: body });
								}
							});
					} else if(event === 'hangup') {
						if(incoming != null) {
							incoming.modal('hide');
							incoming = null;
						}
						Janus.log("[Helper #" + helperId + "] Call hung up (" + result["code"] + " " + result["reason"] + ")!");
						bootbox.alert(result["code"] + " " + result["reason"]);
						// Reset status
						helpers[helperId].sipcall.hangup();
						$('#dovideo' + helperId).removeAttr('disabled').val('');
						$('#peer' + helperId).removeAttr('disabled').val('');
						$('#call' + helperId).removeAttr('disabled').html('<i class="fa fa-phone"></i>')
							.removeClass("btn-danger").addClass("btn-success")
							.unbind('click').click(doCall);
                        $('#call-buttons' + helperId).addClass("hide");
                        $('#phone-status' + helperId).removeClass("bg-yellow");
                        $('#togglehold*').html('<i class="fa fa-pause-circle-o"></i>');
                        $('#toggleaudio').html('<i class="fa fa-microphone text-success"></i>');
					}
				}
			},
			onlocalstream: function(stream) {
				Janus.debug("[Helper #" + helperId + "]  ::: Got a local stream :::", stream);
                // Un-comment next line to allow Video support in Helpers
				// $('#videos' + helperId).removeClass('hide').show();
				if($('#myvideo' + helperId).length === 0)
					$('#videoleft' + helperId).append('<video class="rounded centered" id="myvideo' + helperId + '" width=320 height=240 autoplay playsinline muted="muted"/>');
				Janus.attachMediaStream($('#myvideo' + helperId).get(0), stream);
				$("#myvideo" + helperId).get(0).muted = "muted";
				if(helpers[helperId].sipcall.webrtcStuff.pc.iceConnectionState !== "completed" &&
						helpers[helperId].sipcall.webrtcStuff.pc.iceConnectionState !== "connected") {
					$("#videoleft" + helperId).parent().block({
						message: '<b>Calling...</b>',
						css: {
							border: 'none',
							backgroundColor: 'transparent',
							color: 'white'
						}
					});
					// No remote video yet
					$('#videoright' + helperId).append('<video class="rounded centered" id="waitingvideo' + helperId + '" width=320 height=240 />');
					if(helpers[helperId].spinner == null) {
						var target = document.getElementById('videoright' + helperId);
						helpers[helperId].spinner = new Spinner({top:100}).spin(target);
					} else {
						helpers[helperId].spinner.spin();
					}
				}
				var videoTracks = stream.getVideoTracks();
				if(!videoTracks || videoTracks.length === 0) {
					// No webcam
					$('#myvideo' + helperId).hide();
					if($('#videoleft' + helperId + ' .no-video-container').length === 0) {
						$('#videoleft' + helperId).append(
							'<div class="no-video-container">' +
								'<i class="fa fa-video-camera fa-5 no-video-icon"></i>' +
								'<span class="no-video-text">No webcam available</span>' +
							'</div>');
					}
				} else {
					$('#videoleft' + helperId + ' .no-video-container').remove();
					$('#myvideo' + helperId).removeClass('hide').show();
				}
			},
			onremotestream: function(stream) {
				Janus.debug("[Helper #" + helperId + "]  ::: Got a remote stream :::", stream);
				if($('#remotevideo' + helperId).length === 0) {
					$('#videoright' + helperId).parent().find('h3').html(
						'Send DTMF: <span id="dtmf' + helperId + '" class="btn-group btn-group-xs"></span>' +
						'<span id="ctrls' + helperId + '" class="pull-right btn-group btn-group-xs">' +
							'<button id="msg' + helperId + '" title="Send message" class="btn btn-info"><i class="fa fa-envelope"></i></button>' +
							'<button id="info' + helperId + '" title="Send INFO" class="btn btn-info"><i class="fa fa-info"></i></button>' +
							'<button id="transfer' + helperId + '" title="Transfer call" class="btn btn-info"><i class="fa fa-mail-forward"></i></button>' +
						'</span>');
					$('#videoright' + helperId).append(
						'<video class="rounded centered hide" id="remotevideo' + helperId + '" width=320 height=240 autoplay playsinline/>');
					for(var i=0; i<12; i++) {
						if(i<10)
							$('#dtmf' + helperId).append('<button class="btn btn-info dtmf">' + i + '</button>');
						else if(i == 10)
							$('#dtmf' + helperId).append('<button class="btn btn-info dtmf">#</button>');
						else if(i == 11)
							$('#dtmf' + helperId).append('<button class="btn btn-info dtmf">*</button>');
					}
					$('.dtmf' + helperId).click(function() {
						// Send DTMF tone (inband)
						helpers[helperId].sipcall.dtmf({dtmf: { tones: $(this).text()}});
						// Notice you can also send DTMF tones using SIP INFO
						// 		helpers[helperId].sipcall.send({ message: { request: "dtmf_info", digit: $(this).text() }});
					});
					$('#msg' + helperId).click(function() {
						bootbox.prompt("Insert message to send", function(result) {
							if(result && result !== '') {
								// Send the message
								var msg = { request: "message", content: result };
								helpers[helperId].sipcall.send({ message: msg });
							}
						});
					});
					$('#info' + helperId).click(function() {
						bootbox.dialog({
							message: 'Type: <input class="form-control" type="text" id="type" placeholder="e.g., application/xml">' +
								'<br/>Content: <input class="form-control" type="text" id="content" placeholder="e.g., <message>hi</message>">',
							title: "Insert the type and content to send",
							buttons: {
								cancel: {
									label: "Cancel",
									className: "btn-default",
									callback: function() {
										// Do nothing
									}
								},
								ok: {
									label: "OK",
									className: "btn-primary",
									callback: function() {
										// Send the INFO
										var type = $('#type').val();
										var content = $('#content').val();
										if(type === '' || content === '')
											return;
										var msg = { request: "info", type: type, content: content };
										helpers[helperId].sipcall.send({ message: msg });
									}
								}
							}
						});
					});
					$('#transfer' + helperId).click(function() {
						bootbox.dialog({
							message: '<input class="form-control" type="text" id="transferto" placeholder="e.g., sip:goofy@example.com">',
							title: "Insert the address to transfer the call to",
							buttons: {
								cancel: {
									label: "Cancel",
									className: "btn-default",
									callback: function() {
										// Do nothing
									}
								},
								blind: {
									label: "Blind transfer",
									className: "btn-info",
									callback: function() {
										// Start a blind transfer
										var address = $('#transferto').val();
										if(address === '')
											return;
										var msg = {
											request: "transfer",
											uri: address
										};
										helpers[helperId].sipcall.send({ message: msg });
									}
								},
								attended: {
									label: "Attended transfer",
									className: "btn-primary",
									callback: function() {
										// Start an attended transfer
										var address = $('#transferto').val();
										if(address === '')
											return;
										// Add the call-id to replace to the transfer
										var msg = {
											request: "transfer",
											uri: address,
											replace: helpers[helperId].sipcall.callId
										};
										helpers[helperId].sipcall.send({ message: msg });
									}
								}
							}
						});
					});
					// Show the peer and hide the spinner when we get a playing event
					$("#remotevideo" + helperId).bind("playing", function () {
						$('#waitingvideo' + helperId).remove();
						if(this.videoWidth)
							$('#remotevideo' + helperId).removeClass('hide').show();
						if(helpers[helperId].spinner)
							helpers[helperId].spinner.stop();
						helpers[helperId].spinner = null;
					});
				}
				Janus.attachMediaStream($('#remotevideo' + helperId).get(0), stream);
				var videoTracks = stream.getVideoTracks();
				if(!videoTracks || videoTracks.length === 0) {
					// No remote video
					$('#remotevideo' + helperId).hide();
					if($('#videoright' + helperId + ' .no-video-container').length === 0) {
						$('#videoright' + helperId).append(
							'<div class="no-video-container">' +
								'<i class="fa fa-video-camera fa-5 no-video-icon"></i>' +
								'<span class="no-video-text">No remote video available</span>' +
							'</div>');
					}
				} else {
					$('#videoright' + helperId + ' .no-video-container').remove();
					$('#remotevideo' + helperId).removeClass('hide').show();
				}
			},
			oncleanup: function() {
				Janus.log("[Helper #" + helperId + "]  ::: Got a cleanup notification :::");
				$('#myvideo' + helperId).remove();
				$('#waitingvideo' + helperId).remove();
				$('#remotevideo' + helperId).remove();
				$('#videos' + helperId + ' .no-video-container').remove();
				$('#videos' + helperId).hide();
				$('#dtmf' + helperId).parent().html("Remote UA");
				if(helpers[helperId] && helpers[helperId].sipcall)
					helpers[helperId].sipcall.callId = null;
			}
		});

}

function removeHelper(helperId) {
	if(helpers[helperId] && helpers[helperId].sipcall) {
		// Detach from the helper's Janus handle
		helpers[helperId].sipcall.detach();
		delete helpers[helperId];
		// Remove the related UI too
		$('#sipcall'+helperId).remove();
	}
}

function playBeep(){
    var audio = new Audio("data:audio/wav;base64,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CwAIAAUAAwAAAP7/+v/5//j/9f/3//f/+P/5//z//v///wIABQAGAAYABwAHAAgABgAFAAQAAQABAP7//f/8//r/+v/6//r//P/9//3///8AAAEAAwAEAAIABAAEAAQABAADAAMAAgAAAP/////+//z//f/9//3//f/+/////v///wEAAQABAAIAAwACAAMAAgACAAIAAQAAAAAA/////////v////7//v/+////AAAAAAEAAQAAAAAAAQABAAEAAQABAAEAAAD///////8AAP////8AAAAAAAAAAP///////wAAAAAAAAEAAgAAAAAA//8AAAEAAQABAP//AAAAAAAA////////AAD//wEAAAD//wAA//8AAAEAAQAAAAEAAQABAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAAAAAAAAAP//AAD//wAAAQAAAAAAAAD//wAA//8AAAEAAAABAAAAAAAAAAAA////////AAAAAAAA//8AAAAAAAAAAP//AAAAAAAA//8AAP//AAD//wAAAAABAAAAAAABAP//AAAAAAAAAAAAAAAA//8AAAAAAAAAAAAAAAAAAAAA//8BAAAAAAD//wAAAQD//wAA//8AAAAAAAAAAAAAAAABAAAAAQAAAAEA//8AAAAAAAD//wAAAAAAAAAAAAAAAP//AAD//wAAAAD//wAAAAABAAAAAQAAAAEAAQAAAAAAAQABAAAAAAAAAAAAAAAAAAAAAAD//wAAAAAAAAAA//8AAAAAAQAAAAAAAAAAAAAA//8AAAAAAQAAAAAA//8AAAAAAAAAAAAA//8AAP//AAAAAAAAAAAAAAAAAAD//wEAAAAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAP//AAAAAAAAAAD/////AQABAAAAAAAAAP////8AAP//AQAAAP//AAAAAAAAAAAAAAAA//8AAAAAAAAAAAAAAQABAAAAAAD//wAAAQAAAP////8BAP//AAAAAAAAAAAAAAAA//8AAP//AQD/////AAAAAP//AAABAAAAAAABAAAAAAAAAAAAAAAAAAEAAAD//wAAAAAAAAEAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAA//8AAAAAAAABAAAA//8AAAEAAAAAAP//AAAAAAAA//8BAAAAAQAAAAAAAAAAAAAAAAABAAAAAQD/////AAAAAAEAAAAAAAAAAAAAAAEAAQAAAAAA//8AAAAAAAAAAAAAAAAAAAAAAAD//wAAAAAAAP//AQAAAAAAAAAAAAAAAAAAAAAA//8AAAAAAAAAAP//AAAAAAAA/////wEAAAAAAAAAAAD//wAAAAAAAAAAAAD//wAAAAD/////AAACAAAAAAABAAEAAQD/////AAD/////AAAAAAAAAQAAAP//AAAAAAEAAAD//wAAAAAAAAEA//8AAAAAAAAAAAAAAAAAAAAAAAABAAEAAAABAP//AAAAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAD//wAAAAAAAP//AAAAAAAAAAAAAAEAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEAAAABAAEA//8AAAAAAAAAAAAA//8BAAAAAQAAAAAAAAAAAAAAAQAAAAAAAAAAAAEA//8AAAAAAAAAAAAAAQAAAAAAAAAAAAEAAAAAAAAAAAABAAAAAAAAAP//AAAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAD//wAAAAAAAP////8AAAEAAQABAAAAAAAAAAEAAAAAAAAAAAABAAAAAAABAAAAAAD//wAAAAD//wAA//8AAAEAAAAAAAEAAQABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAAAP//AAABAAAAAAABAAAA//8AAAEAAAAAAAAA");
    audio.play();
}

function playHangupSound(){
    var audio = new Audio("data:audio/wav;base64,SUQzBAAAAAABAFRYWFgAAAASAAADbWFqb3JfYnJhbmQAZGFzaABUWFhYAAAAEQAAA21pbm9yX3ZlcnNpb24AMABUWFhYAAAAHAAAA2NvbXBhdGlibGVfYnJhbmRzAGlzbzZtcDQxAFRTU0UAAAAPAAADTGF2ZjU3LjU2LjEwMQAAAAAAAAAAAAAA//uwwAAAAAAAAAAAAAAAAAAAAAAASW5mbwAAAA8AAABHAACwUgAHCg4OERUVGBwfHyMnJyouMTE1ODg8P0NDR0pKTlFVVVhcXF9jY2dqbm5xdXV4fH9/g4eHio6RkZWYmJyfo6OnqqqusbG1uLy8v8PDx8rOztHV1djc4ODj5+fq7vHx9fj4/P8AAAAATGF2YzU3LjY0AAAAAAAAAAAAAAAAJAVAAAAAAAAAsFI0loDXAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/+7DEAAPAAAGkAAAAIAAANIAAAARMQU1FMy45OS41VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVTEFNRTMuOTkuNVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVPWkAIEAAIgACtOmDQBGRgoAReYz+UnGDaQZMPzxh0IRKYUOCEn6Vr2JkpZUNLMzAuAJIwGkBnMLWGUTCGQYhnAwHAxAwugzAyHrVA2FtL4DgAAYJgeAYKgFgcY1GgZaxEAZJhku+BhDA+BhnBuDUCwAwLAMNSDAOcbfwNy53QMNIzfgYLAAA3jDVgGAIBgGAIAIGdFI4GUkNIGM8UoGQkVYGHkT/4GBsAoGDUDoIQGADAoAwZAYBMC4GMIfgGQEGQGFIOAGHEYIGQ0ooGJcVv8DA6AEDBqBEAgDQAwMAMGgCgMAIEwGgHgYLxDAYownAVDUBhkC6BjIC6F7AMEYPP+AEEMAQBAXsAkCADACAMUcHACACAAN4DDWIwDCcDoDCcAUDAcHUAwGgIgdgEhMAwLg5AwZAK/+Gmg2uLeDgBhZAQgZgLCxbwUAGFoAGAYGIGA4DQEgpgYFwdAJAuAUEwDA0CUDAUAgCQXwMDIKgMAIDf/+NgOADFZLifg1QYi4Q1WbCpCdDo5ogmA0DwDAEC0CgAgME4BQMCIHggP/7ssTOAABAAgAVkAAn4kVgIz9gAAmAEBwDAoBUEgKAKAPAwBgOANASBgWAMBgQAGCQBP////ODiFKEXIKLLSG+LkPDQIGVx3kAKjf/AwIgBABAkEIFQMAAAAMAgCQmAILFwBQBBkMN4BuSKAEbBjYWMWFlAoB0YKKBZGAVAtRgiAYuYjMKzm8ifAhi0wssYtaJMGByAZhhLAIEYGUBamDQAyZglAEkYCiBJmBqADBgE4C6YE6IgmE/gYpnFMlRJmRnSb7JBxU1GuB8Y9RpgChGwTQb+ChvhlmW2ebWMZtAtG4joYYCxxRUmEyuaNGhqGGGc2Ic7bRkaIGp6AazTRn2XHH18bCk5pI7mYB0OBkwIiTT5ZM6BoyWETJhHBpJAocMmBsyGKwMtDOwVMsCYwkGwaFDDQPMSkIzKejDZmMpgEwQTTJhEMSjMHBQlCwYPQoLjCIYMwiElGpgochQLgImAgUiojMYDQEA5CYBQug4Y5EQ8FhGFyqIE6E9QgNBUEGDAE1pM5VNU6TpED3bHgOCQoqdG1kY4BlTR9tm5oUJhxZWle8ZqMtciVQiGKjfw9In0bE+r91HveaRuTAMmb+ci0bgJo7TVO4eZBGKPB/38dKVtQj6/O0V2AGmKKTsMrTcFukQ+zdiEsg92oDr1akajUrwhu5BlFC9w9GpuaizoVolIsoIe2TO/VosJTdoIvD8+aZMAIAaMAQAJguBTmBohOhhYwzednX3ZmMhAMZhcoLkYVQFBmA6ARpgsALIYh+CDg4O7C4EEYEmBRGAbAQphqQngYRiAHGz2GYMZIJMhpo6GUGkYQNBhg6maX4YVDJq8//7ssT/g/QlswYd/gAGRzhgwf5t4Hgp+GKjQa4S5hNSGhWYaIKxp0hBHsDhya6AhpS5na0wZeFprkQHTigbfVBlBGnUYRqtsBu440mAhSfy1qxGagZiB6Y0MioceUdl1DJBw29uDCQ5kOMpOwUIogmqDQRJnfmRigMOFpMRGNkhmQmY6PmRngNDjJhoRMh1RSY8NhYVMLKhwPKo4EGwEBTGwR3xgtM/VhYwIQpBOYADDwMmyrTToAFpKaJzqfWKjkqNE8tyHAsKc2AmUsoXVLmuLxqQe+cpisCtjau1iPOJLmsRptLT6zLhvtUkFPYeKAo5G5RAUNzDN67XGgwLSQXB0dgp+mJMJc14Y+3KEQ3RxWZk9eG7zydvy/dSjpuYU9qSw5HpVKr+qairvvDsAzsT63J15izr8t1aKt2K3o/LnIfizK580//WMBRANAuBVmBMAThgsAHyYdSGrHyERORleISsYTwCImBAgJJgRQDWYCqDGmG0gCoXBOTAfwSYwKkBDMBeA6DCqRJowhgDcNKOQyoUjQI/MYDg3GFDPhzMBEQzwLjOghMJWcQnsAHUyuUTBQgCikOVk0zM7zGBSNZCw3ZLMpNTE6QHsB7hEaa5GXOh6LsaK3GhAhgJoYYEG7LoRjGFnBgpYWCkACZmIaDBkyQEMQJTJRExpkOUGxZ4MeVgIMGAhJlqsEXZq5wa6bF5QcpGNg5hhiYCRgoZAQwYmOAopMGCgaCjI+ZCCmEEBhYuleY2DjAAhaACJOpFhJNS4wQAHguKuUjUXdZU4xVA0yGoDwAgJRYnUuIxKIbdqhYWy9ejX3/d501hoCYrLnGfp//7ssSVA/HJxQYP827GAzigwf5p8Go1KJuNcgOBG9ZG/rwvDFpfE5pt9zsntPYy2MNJjL8PGyJ+r1NWpN35dAMbd91ZJBLoyjs/GpFuv9eHKv5UnaluXT927ZgiGKSpI5dGLtPPv9N5W///tfq/9h1YKwgKLvDOf+eMBqATSIC+EQFeYISAfGGhAah9aKD4ZX4CxGEGgrZgdQDUYFgCsGBChZ5gFAPACAGIRgQZgCoEEYCEBJmD8izpguQISYsH5mpfGZBYKLA16ejHoONHAkyeFzI5dMExU1OTTE4dMbD0wIDzOIlNAMQywDjUaqMhJgxOmzQT1MVi0BNUzkBjDp/NBG4xaczKI1MQhQSK5g4amDVeNhwHA0xOCSgYmAAKKOEwoEQoEBGIDAABT2NFq0xqOgYBQQFQUFB0yHzPDx4tSLDBKMJlTanDEHTAhR0GAbCp0JoO9F8woOEky5lpLHBAMLFDOLwEOBQcwAVvCEExCGmt9SRZamFPCIA7aFjc2cJNv9AiYsBq2Sxoa/3FlaqrcoLfRps3AEMwUt92nKeZ9ZfTXrEVk7lSCN2JbHrN69DlqMzeoenYdhcumnZjFmmrU9E9z+ufG5RjKYtbgei7jO34jIdfvXZqU16TX7psKHKOy1m/a/eZfl//+PMn85BFJEsIKo1hLP/uAIwBoA1MBaAWDAYQIUwHwF+MInFnzsyK4syN8LXMImAqjL8wzKMaTJpWzuYCDK0uzAMdQAE5hqIJxVlpx2IZg8OYK/mlQRgpYEqIKoTJZYyJhNudQacn0lxtycYiYmwHpZAxz3MKBQNEGKMZl6UZXNmqHxlZ2AuA2f/7ssQ8gaz9wwgv92bUZDGi3f7ooIeMfeARIGdlJiI0ZahGahZhxkfMLlxRUHFg8eTjGAg3MBJlMtAYELhYPM7WDCy8xg4MUFAuFmCThWYiQaCihfYFBgMzjAYngYiBKUmAjgCMjDwUUEFWIXQ2zqiRGHQVCWY+BrwV6rEl+sO0xj7A15tPfVwn9dd5JE5StjcWGRtUj2MWkKlzS4o8+DRn+hiMw7DsZirqO3Q09iHbFSVSGN7vUE7aj0EOg78jeLkTdd339gm9NRB4J5vZ+u83YY92JttoLoaeboqLPtX6fv/+6/YYv0v/9I88t5chp+voef//////nM2I9ZoM3onpt//TEFIhUAGKgCKYAoAsGAIgU5gOwUQZb2v3G6i3GZY8mKQrGDgLFgQBK2QMjMlCgIgQMjFyPDEMGhAXCJJatJUGh2tgEwoeoMQRA8sWAZhQ7HHCHYACBEh8wohfBnnJwB5cMxgAqjgIECqVHFDdBMFQYyqMaDkT2Q+yYddDoh4wgGShXHDMrXXlVRXaVWRczACA1owOr1PhQ5g70r3IkTI24uq1Byp6Luu9tcOFOpEHbgVbdFIqebnI27UN0kplcAQRDkPRyM2YhWgSKs6uOnAsrgi64kukU/bp49D1uxWkuPzt6/STEtvUWr9NIn3vzUthmbjV/F3ZZLp+Vyx/prOUXZfnrDD7OeWW9d//+p2/3L//LKpKrd98iDUwAgA5MAzAkjAMwNcwEkG0MAGF5zBF+DcA4mZGFUDDXMeQVMSnyM5DtFrPDBQEhqMSAaOQ1SNxBAMwfDAEYyEtCwqb2VAp1MvLkHyYrMg6jOSYUHAMNP/7ssQrA6etvQoP92UMq7hhxf7soGRhRa03qBMkBiIBIBMHMhl8abINGbhI4LmiHJhwwaIPGhEIMLxAPmBCSRJ+IeBAIuIscdGTJzQIvQKOiwAYAHo8HAkqcwGBCUABIMYk9Cyq6aIwcNokGQgqGy/jBxJrwyNj0kkehKnAKDiwuOgKjyv19wWBhxDKrLk6HpSvWY+Dz8YbeZQ76Km2fL4n23exh0Ex2GXFbi/URhm9LIcjsBVqnZ+9fmrt7VrP61y7hhLdTNLSymW53JVjuzytb7T35qp9blSpqkn/7Ws59nN/Yt///f/+///+8////////////V+UZc3ftKYwCkAyIQEswFUDMMB0BHzBTxEQ04Cd4PdX2NOjlMWRAMFxPMN02NpRnM2gFMDQAKgdDg8mBftmHQdixWLCxhIEYOFi1oYaHZGKAKFRhm8YsOI4qbmEAowAnCpBhAMIBFeZCAiIdNcEAwJLLmPhYAEDLR53QVBiw24JgJyaWPIxPEDQEUAxA3mHCbeIZpBAEHMhJI2CgBCWlyBTYBNiCMYAhoUUABwYpepyqRL8RjYYpQw3N4lKF0ricxDddyGREUMyd7lmGnHcyDIckNLFGTNgdaOw7ejVPAvJbdn7GMxnYc2Y5k/MYqVJ6pyey+13GW5UtnOzZudy1Q2sp/Wer3L27OWV+t+XJNumucvYa5r8+/+H//3v//////////////////hygkP/LK/3VTAKgEswDMAwMC2ArzA7wWIwowQjOa/jtzH/gecwcMCcASiGDIiGFI/nuZIGcY1GJANIczD0PTlQRjfEKzMYkyA7MQHhwMEgQQCY0f/7ssQlg+dFvwoP92bMly7hQc/saDGMBhk4MY7UAuFFiYmWTBSQyMHOgTwEWAAFMIFBQXMMKxsYAownIY2KCRwAEcYFx5FTJGnolaTrAQDAKgKg4jBjSEcefnbBw6CA0ACxxRKsIiE8rvAYyB3aWmBgSBAIKAYKNwsHFsBADlzx0xBQssEDhJQJq4iCA4Tm2UPySChiICHBqjKqrpM6UefiGZK7WTxwDE2RxyDXDgOTPzAU9Ov9DVPGLk9Xmr0ogbWFFy1lZvXLf1OY7s4a1q53Hfe0Vymwscw3awsWdWMsZHe3JMfxw5S1+8/6/f/+//////////////////7l/M/1DT3YGOQsZOAxpEDnhhSYWeAxHYfFCxkZIDOYR8BvGCQgOpYAVTAMwa8aDggYBDmAGALw6AQkoEUYFuKCGAtARxkg8YYOQeLCwRjGGFBiwNDRhyAZablMqUDw0PhQBVWPBRB4JAoAIAIGiIUGAO6mNDIOFQKFGIhwXQgMbJho3lUBMoDiORARIDgMWEjBQYwOGJlMFBqGwMFjBTw3MRIhohA0iQ4FMSJQNcBgIpSCRMYATJAJTYGg6o1vEp6GGKqrlKwK+Ym6j9p9repSZSZ+1ZxGTwZEZZG6V+otKoXA9Z/H5euEw3SRDCO08aiX1u0dWWVpfzmeFm79Sd79fv1fz1Uw5vtix8ruY9qWbWeHzdLjatar0+tUm8e1rmFf/+phT2qwT//gEFcsA8IAbDAUQFEwIwDMMEvAhTDUg2w7xd5cMiABzDBqwNc0aOgwkNQZjs5SUQyoGAvIAiSMTg7Od4pOIgqMHBuMGQ4LUhAYGHQfDP/7ssQkgKclewgv92eEWK/iaf7ouINAQBwCCxgUBAjTsyYAsIAsvuYICmNAx5hyYYOA45QcMLFTDDoBhpcEy0HMHA1MDNVsxwQDhkyYbyMHmjIyMiUAoBAQOC4gY7CGHBhg4e1QKChgQGBFAv6GDIiDUVwawmdEZZwwEXVVEhEz8SWsYADAQDJgIAGIOcEOS1l2O8o/DU25S0xAGmGAi9mHLCNFeFnFNJ28ZS8DWWHUULZLOvi9b9ubDsr5CHZdZ/alWN0nJ+URWUzOcxuvSRaf5/O2qKrfmKlijrWafsxM40t7UbwpZPbnqDGfjktqzlLZuy7Gj5Uzv9wxxxncdSx3/9f/9CAECC20wAIAFEABwAQE0wCwCSME/C4TSvGqU+HZ8woLYxvGUxVA8oHUragzvCcEgHIwKH5k5YJkKH5gyFoFAkAACqkChhlasAyAgQGgEJ8wGANWpAQ3MSDBttmj5LCgwCYaMGtYXggNXOFg4MIhcQXEMyCQJjftl6Tj4uaDSpkAYjAMUZIiSZ4KNFE4XcXSMuwwq5VJHGGCxRbT/IcEFGlkzSFMCYLC2YNTjkMP+0oOWUvHyn4zP/Wa+1J1X9XO6q8HpxcGFP/G32rQ7MRJhbPeRulls5FMMb+E5HpiJxWmtS6Q1ML3KmMY1aj3LcrnY12EX7E9L8vn4ru1K4zHIzK7LXqe1hHqTKrdlv6kUutat/Lqe+j7agKAWGAegToNBSjAnwb0wSAa8M/x9jDuD+DQVGzOomjRAkjFNfjtIizbgKjFsNzA0OTE8WjmLQib5zO1sz5nM1AjLAw3slBISZSClzzDgA0TxDU8gBzKQ//7ssQrg+JxfQgP92UEra+gwf3p0MRhiLJ8g0KAyvA4GAIkF1wpJUzTFAwKERIImDJTvCgiIw4AExjjScmUBA+XiLiAkMMQmRoqSPIgEEDxUFTpQt1hgbQWLtCk+DiNQ4DBhdgvKAkd7gsE1mivMLVpdZUNuAQUHrnf594ZFAAKg7CEG4IXuvB5u9lT+wLBXY5nH7FSLUuqWtlPar38MN37GdnG7hjruF/n7w7U3yhw7N4Z5ds97Z1le1/ceYfl2tyewyva3ruP73jz9fz//Gp+owEwBFMA1ALjAxAIcwdUAvMMUEbjF5+ok0QIBiMSdAdDCmABswSgC1MAMCVjBowIwSCFjAdgCswG8BkMALASDCfRD4wFoAINaJSReNFXDCncKCJhg0ZGEGEHYCGTAgE7kQMqNTESoHECq4PCdHhAQyM86MuANm8ML1dUz74aEgcWcqOtIGDzDBAFPMpFPozMMMX2CBIWAmFgB2MxJM3SVZIY1NIqMifMSOCDpdE1wcIpMwMEXRDRkZQXPQcMiRCFpjRoWGhgMdAp9rCoFAUOTFHKhIVBBgJcDTpyyyqGu6+/uh5bxktLfi34Z2LWtV+Vab79+puU41sdXbNfHVavZys6odW92cuWucrY41JnDt7uOcuzqdpcu1q/ccquX6v6///v//1nchE////bAAVjA7BRMMARAyWTjTSOMsNxU1Y2Dfjj43cAN4xj832yYTRXPjMlIyYynx3TLaDSMZsaUxFBejDrIDMu4NUwoRGzoZCM3QIBoY9ksTcoWNkRkyGlDC4DM6M41MqDX4oOnEE6apDlEhMgNIUmpv43G/UyeLARsf/7ssQ7A609nPhPcy+E4rRfAd2yOZsm05gaOfJhqPGEXibIRxtEQnEC6cCSZv+hGFl6ZyPRmMjmigAZlPRjY4mAUQZWKRlsSGxDiaJUgiUZg4tGRSSZiLBFAzCI8MLAtnAGTSHRYYyxxqgDWnOqKem1Cd/oEBJLD1aMVQKFmAglCZwYAEThTHLTGCPG3DkLT3uZfDjL+3HltKrO9ZgVw3iaTUjTSpDK2hROSxejf7LB4X8ldK60X7jcy0/kNS/DKHqaMuNfuuI7NHB0fkNWixtRWanoZlsGVYveyh6byfaNUcllmMsh/Gn5MS+Hpqz2USiVXu7bjOO/QUkX/W4lGI72OzGcfTb//9jamAZpGBaymqcuGUqvmpfQmoUtGsrsGJT4iJaTPRJjMEWTEgFTDoGjPIGjJQHjEUPghCjDsBzAUlQuIpmCMhkIiafGk1yaIxGEOQQwmetJlqEeCIhE+ZCmmng5v4UcOpGVpBhigYUImIloCPDUhswFuMzlAonmXxgFGR5vM+dDGTQ0JbLLGIno0aiSQYGEGVgBUOwcIDIOjshOM3LRgoMsDxGMAYVIAOQGRkpnQeGHpESERUVTgyZgMJDy9ClxUGzEwl/wKDGOgwYPEQJG0rR4DRMQAKaVndTbc12s9ejEM8KhWJZIVoZaRL3j5UH50oOqpnmj92p4/nXsuWrH6GC5kuU40pWsBS80LjKaCh30CwttMKnPZbpG+4y4nzWmFqdlpiO/MVexhuCKbzVtiZvLmP7OerEH9XAVABWiQKmlxoZzAxlt2mUQOfqXZp8phhGM4nUxCXTDJQMiF4yuFB0JkAOMLjswgOSUEv/7ssQYg6NJvv5OaTHMv7hfSd0ycGTA+ZtGZjExjAyOAiBIIFDDJBgQTOZxBq0xA014oyTQxxswIMLwDAkxUmAEBsjwKTheWMLTvQzQDQQbMCNMqfATMQmAMPMEYECRfUKITyHxmDAchEhy1WlkIAypGHiYNOqIpNlnTADRGNT0WBEnBQxGQQXDC0RGpdymhWJowsLWrDNR2l6PvEYnBEDt1hl+f9GkTKGtLPRk8SpZRlhybIYJ2Ey5lc20ucOykMIoZuvNNlRW4TMuBsqdGhZldZdBkrjmSpaCGSAlNJtUlsSXCUlTgnKOOxvIxFXfUGlP/NAbX8pyht5nhjE8hHCg3mIKKmJoKGWgmmKiAm0cbGUZfGGQMjxlmFpKmH5RmIJKmAIZAUBjGMTzB4HDB0Ug4WBAAphiDhhuEpnmI4siphaCY8IIiC8FfzWUjhxjJCTDnzVYTeFzUKzBqSKScskbdmahwbjsOIgskNMVMezNcdMEcBoIzpI2EcwCEzLcwoMIJr5UkIyAyMTUKooEAjNCASjHEBvC5UDDw5Lw4RhBVWyAS1o66HmgULHKaG2AES0MCTSVTMDDiUjhEChx7G6P60JRtq9NDkth7Ls5G8dWmYThMeLvjOjPyqHyx7nfhtkHUq2vZw1qtY+hZgq9FyE+ZLzVGogbmrln52XnW10Ma9xIPHpaUgODROfny8zS3dhPT08Kx7CNMDRWLy6Kri+hgpNLu3ut7Japd199m6oABbJBaZ2OIyzDHZhDmude/pjREmyy8DmKYwJ5jcnFYdMcgICgMxMKm6GRiCYJEJkwzGCwuYVB5ncvGFAxrgMFCMIM2v/7ssQiA6WdvPxObTHM7jhexd2yOEGbiBnf+GDIBCCIFMnTDJD8zcRMpLA6yMCWzLiozgWBokCiY1MUEJSYKBiEdumKngCYDFQYx4SMfEDFy0yEdMMA1ZjAgww8lT1f4mRxkMMKETFQQxwvRKMlW0t0qEFwAGDx2JCQkzAQENrSzIsAYFwsdmFrBlw0KAAQMA0UEIOCjdR8EAyHNqxAAg4DikIZ1f//98c/6SEkPiRpXREunjYoMZZ6imJc41zjKgNNdYlgjudeaAdbZIdYEmFpHoW0lqs8UJeRrw5jg0xFfTCYY1TUDRtCRPmtAqV1SPPEo8TgzeXj8d/dxZjiEDAOYdEialEOZJm8ZUDEaCxkYZLSY0AcYyDKYWCAYlB6YzjyYlByYHBMYmBuYHi8YankZXBoYAgYY6FEZDCCYChIZKemVKwQ+FJmbOnGgLh0EMa2TA0IDoovoa8aGQlRkwAXZDAA1YCN2Ijdywy5sA2+ZgpmisZm4Mb4vGLlw9HILEwiZORGLlBg58iWYIEmWlyylSprhwSZOGMrGS4CCQCBzRB0BDoCCSAEawYSKEw4GIJhZSdI6nNJpp6AZSeMRNvEHIFQEEAplpJAQ4HhxyGBy2ZIAAKKNKnr/fmZmZmZzlUtPOFo+M177xPii4zxmODqHlOOY3aRwjdesqrWFMinD5m2dRnRjLBSe72Vk0ur1ZmL1+OvLGWDs4U0diE5ppLjxyrP4mC++nQvxc/0tQn16bX9qsdmDUO8VTAQPMImI1+dzZ4HMrmkzSiT5ASMjOQ3KGTgrkPhFowgTDMQlMcnoy2FTLzoKEIaqKpn41mpyKY4CP/7ssQcg+UdwvYObTHEnrhewcyzUBkovmpApkIGXRMjbTCyEWww7uMxEjESUzJvMR9RECAVxFCMMQgAKIZmYHJmxWYqbGjER3oIYekgZhNtMx4HEicwMrByqRII4HBgqFxgHAMILxr2aEjomiUC40LgQDlIGLx0BGR0xUhJS9D4RiCWheEmCDGBZSBlgSYoMgQkLyBQYlhMUERMlSqVNRzFrLqbyMUcohyvs199ZS+/ViAjguT2Dc4npTeDyyUVCRBZBibkCTAeSjSiKiopSUNAZLITpJ3mFWESy8YzQqz6eTanBAmgmwxBfFJI9VP5rHWVnBiSjDMLIIo2IoD0V0SlZsFkOoymUy2YzmxtsAHRcOc8bxk9hmLK8ZYnRuNcnBzaYQHZhsKmWmsZiNxk8YGUEmaDCY6ATFpPMABozmgDEZFJg6YZAQwATLYeEIDDiQWvS8LtGUQGYJCo8NTAo5DDqMFwYD5gMKmWxUYNE5lwSkoVMDi8Cok3CVyYFBA9MJB0wCKWYGKiGmcBAoDnBocLLpEQKXpcREUmUD4X/JlRoUYfHnSSnLhoGGWUnmf2o+QPJl3S7LHgwswgjRPMwlXNhQSyylOWDltQ5Pw/OvUSn699tomcnKJVFbJmbQNFREyT4/hPE8npjq+KP4TJ66lCKVzpUxBihmXzlcWkt4ZpRtbFkUX16H/PrNXhPfpB+0fYLk/y3Ur9rVX+50bCdjWqRN1aTx/ezMfbSLnVYggC6267RiBWF3k2FzMjMzBFRBOFV45IiAhgbmCgU7KFwwgqFCEv6AAAwk4EjwtSpUPLokluCHBqihf6XFQj+ONH0AjM0v/7ssQjAB3xpQbt4TODqrPf2c0aOUmQmA6lySbnM5Xi+bqIARKRnAveepErGAPwupuSaDvN4v6TwM4DuMLciHkU2xPAy9GCHnRStTiSJPmUrcIfSjMDTc0KGAykV13w22Vn0cUCdxy2cNyft9khP2eQFMJ8KuIxPMhXI+jZ1Pa83wegNsPMRQTKq5zyBF+pldScBfM2cI4RmHqbceqambIMtVVxZMbaYhZNhTDK7kZ9DAnbUmw6JpJSFo7butFUAAJAr9FQhGwNCffdoOgxkiAgo4mh06aqXBq9TmKigZED4XH5jIPGPiWSD8CBMCiYxmMjHQjMIgowACzbJAS8aQgPQSmeKAWKMATCnwuBXUkbJmsqzqVBgFhbMmjBh8UBsxQ0MMOSCGiskREBQthrWFgnZWAkaMsvaE4jMGdsVeFlrsRRdyT0UjvVUGuBUMzZ16WTr4lE7DLlu7HX8ltWTxB/6vz2ymMZPuJCBm10Z8U+URnDJZxFFs2wsvY94849Q7JXpIPJf2yiEmzMzFzkEIaoYhsUm5kg1K17RUe0u1XuFXJ05qO6yWpKqgA24vCYmeGafRpOsZgWBwaY+bAxvMmNjAHI0gnbkYSVjRaaQMGcqINChGBsDR9JkNMgHYGQaiCIxS/5isHhYskRlIVr7WSmHHHFaRVAgUOyJ1UEqEZxsmCCsaMo9JAy6HX5XYXoHgGbvkx5BOteQQ7Uj+Kt7A3LXxKWlumueGJS+V+MUKqq5WnxhpctilqFuiu/KMW7buwUBnsiaRofZNtXCTnfVHEsU7lmikyROVoJEvasq8T1z9gYTEEwoRgfSRIHpZGGg70fYf/7ssRkg5yNowJN5NHMI7YgBd2iOmZoLtkUyMG5mD9rJqzjLz53Qqfd/DMFDGDtfKRAwCBSYzm4cUAoY1j+MCgFQTMixTMggiMYw2MdiQMJAQFATMHBrMVgoMGAST4EhXMMh3Mag4MMg2MKQEBIyYuViISMhEzFjYwMVASuCmAWDBgBJRAxguQ8MGGjPAkZHDmuI5piNeKDOgI0l1OhhzUSkyIgNXIzJT02FDNFAQYKlxwMFlAEYaGw4YCClp22exIBYiOAkVz7IwsArUYoPCSsb8KVsWGgQqgZMHRan4/L1V0Py6amyw678nIjd2J15qR4yBB42sVsZIw9/jFhfm3MDkwg8UEgpYqYSYNsosPD5GqIAjUZbiYaQGnZLktzfv0c0+h4LX0dTi+l/e540rvI+W/Nvu5mNzWqAAVhGIGjHJjlUPSp98AThoOAzTD0y4EBRQbkVA4jMOGDBysxMXMsCzMw0xcJEIWYSKGbihlQeJMQMGzDCQEjJmwSygQD4qKjwxL0UgsGplmUiZsIWY8QDIyZC3mfAhjVKZWCmVBoYWHGdIs3Aq0MTCQqFEwcMjiIqzi/sVKrVVW3HXDRhySmyAVCWnWXgYCn8/SWFdTEMGv1ZraJaTquGwN3afArPVdRCJRanoqGzTXMu/vj8sxT5F6qqtqQb+31n3r8+He0HfnshAwgjcnly0Frj1ubDvFbl+6/NUtTZP/bXQf3yqzfUI8gv7KP4LtZh4IMANx0hBhg4OmDyIcrKRhkVGNgEYjGRgExiEQIJjBAqMSAVEsdDoOGKDJCLULAUMmeKOixlB7UBhBr5j2yOhiIDUQYS2yokv/7ssScgJ4llQZN4NqLfDLh6cyaOCGRAAA0whCQNgmKSX3A1hoUmdoAeTDdPEkZWAiIKBRsib1sVVhaimmsFGVglY2mteeVPyWMygGD5prKtTcFakrG1e+AYKZbAEuWAL5Sl3oo+8WcmRTFinrYf/+/m7k/WjUunHFJ/tyJ2dz/zzIg+inujamOXXRYrFlJUtvRS99fPvg784uHMz/8reib4+muVqNkOtwge/TVAFDocWImpxx81MbiwgE4NOSkTwvambxpu5CYGTmLDxjgyFRUx4KMOUzNYo1kQVKYwFmXlRuwOKiRixmY4qGNqpsQUaSWGlIilRiwOMhgcCGSvJvMWac2nY6Jw8uMRoyEGurphEIbUvm5GQZVHGHBssCYOPlvwg5MCFC0gNMwcenVskacp5oBQQGNK0QAFTAxAtqDpw4QhCMGEuyFghhyXA5cECiFg7ogoQcBiI4KLMIRIpfTaLoWirFIGhPpFPuXv+GQ6ELKOSqj015Pv/CL9PLvxvL1akssI8shouND4tFxiQiFUuWhbjFq0kcqVTqFcwKALDE+E2MRQHwzCDDDQltBP43c82JTLjMuKNNXlDEzAgnDPBuPP38x0UTLSnMsrky++DtzwN3sI4UQjSbXNyGgy6TjDpKMUrI18WzGAVMypY1eFTqw5MSg4yiHTB4DIi6YOMBhJXHEl0YdHRm55Ab5ALPGFSOYVQBo9rmr4saaP55pifAhmGpJnJWa2GmnAQRFmGAhkwEZEfD1UDFljpM0GPgRoIEYkuhA4MCAs9mCiRtyIROoWDTUAgzkRMcFjSyczXHMpCQoLB0+b+hg4QM+f0thqP/7ssTjA53pRQYt5HqFOTQgCe5tOWRqLAAKCyzEvVFUileJeL8i8WbLT9+pLKkjwp4xfv97U3SxOkgCN0mFWx+Ota+zU1a7zmeWNqxeqTF+5SW+9l9but6vWez+9yujms7WVzDm72O88ocvSy9FOWfyrVpXKLOOWd7OzjSynlq5Lr1Nbqzd3pOiK85bFQJBQCcYEWBXmCYgDJhPYZCYN0MdHGfWsRlkgooYWCBDmAkgdhgcAIIYDaAFmAughJgQYC6YHmBSmAmgIBgOgCiYOuHJmD6gNxEBOGAzAApgIoE+YB+AAm2URlgACjo18AAISAHI5o+MOLEOZIFgouMVeDMi4z1SMyEzd04VcjzIQ04eGE81VOHnQ1Y8MsPjUicw8TEAqZ0eGfIAyfmEgxiAsDBI04CMDFwgPLqKRAoEYUPFnDHRQvwBkwxkMDk0aDTBRElEQUNGThaxS6xVLAM5AIYEhRdTCC/awZaVka0WtP+0WOyeWQlrDoyPHQmHggDu4QFeMF1I3/5vtoh6Ir2nMjOk63c6PZOiFkqNZOlKTAVAC0wQECqMBIAVzAswUgxJYJlPn3trz16FBM+0jgyIQOjBgCAMA0Vs1JyGDFjE6MGAGEwkghTB7C7M04kMy5QOjNJhMQpExALTFQrMKDNCAHCIxOCDGICMd3I20Nx46pUjATGAIZampENwgbmFgwQl4xIPgl6GICgY/BxmcAjBkNGlUxiGDIY+MogcwaOzMxCA6QHigTAAxEBCAOGLV6KBsxEIyoJRAKhwgAUsg0GGHhuYOByJYFZgQVGIBxKDgoYVLpkEwGLBIYKBBikKA4YixhIlIf/7sMTzA6IJYQwv7LHE+C7hAf9woIUA8HBwwLJpggkApyO6wUQgMyGDEkQ4LxNnMHMw1m3Ogj8vp601P5VL+qLOv//dsYfnn/4fUw33D7u9X7m6v/q7f1bw3nb7Z/mc/2kwu/qvq9jXrUlnPGvcw/dipuxh9zCxXHP////61TAyQB0wHYBAMAxAwjBlgJMxUMF7P2ACkTLkwN4w5gEqMDpBozALgDswI8L/MHLBFDAbgNkwJkASAIAwYDUBVGAhDhhgiYFcYIEokSTDZsFUKAp8RHUZLJkEMGZgcYPTB1YCGVyGIAQTEAKgEzm0jGAiBojMSiIxSADF5uH1olIY9ABlATgIYmrBKkkZEEmqHyOBkmgYYxtTJAExQUEjw1DLN9EzDQgQDJhA2YYRmorwgHkOxggQY2CgnIGsQdAjEAAwMudEzhLCAlI1fJkgoChEBdAsXkgMAgFU5gQg57EWgKJDgyYoFA4WLbJ8y4QASr+e+iwT3xClU5jjDrer+p2xKP32rVpMLFPP2L1qvnhnlUzysYWcqmOdJ+dW3Uwt0lXOpq5Q4yzOesb5nUqUOFFX7buc79Wbrcqc+xZv4duv////6TAhwFUWBZTAjAN0wmUGzMSmGGj+Pb+Y72CkDMpDaMbQTIxXBJDC9L3NDIVQw5gig4QoYANMA0BszpwnDLsAqM8HoyqwjBomMfEUy4TEwjA4lMZBIwiEjL7dN4BVqBVEJgAPGDgibWfY6ECYjEg2MICswopjlw3MBhMLAQAgwxSFjMsmJjOECEkFIJDhk88HpxoYdFhgASjQKBoIMzQgHTovWUGMuSXgNfB0FBUwqCAq//uyxPoD6IF7CA/zbwUFruDB/3CgKAwPGAUoEWBHJ1HuMHBoxiXDA40MBilW8QBMwSMiaAgAJuoJCoQgYZC6AVDZarJ1gjIgBEgshUgiT4CoGn5HhG3/lkpiDQOIyX7tutdpsuU8H1G2nX7pZXevdorFXLfzFutyrqx2tzLWe62NHhbvVce4Vd3r9ivWv49qY9s9sdwyy1lllh/fs91TPk9Ozl///QoABpMBDAJzApgIAwNEENMF6B9DChxcc3ezClMTxCuyIJpMApAPTANwA8wKgA+MNIAYTBGQCcBAJJgAAB4BAGMwJYVrMBXAmUJJiEbkxkMIgQwoMzBoFRhAQDDCAYXqJlwehQIPKYIFEIidHKGFADOzDRQwMsEGocMAltgcMjA8YKKmgxokQGgB5ihgBB4y1VORVAYLggBQ7A4yMfsDJgYwQIW0jUQhxnoqucQAhbtLsws6FvRVaGVFUUDFD0Cg4GFBEHmICZj5QPGisaxIChhRhWyIOEglLlCwupJojsqGxNVuW8Hxm7E0/tpwopX3/xHPlWs8DfV5buWX61e1hT2Z799zu1N6r6797l/HDHm7mXM7Hd44/q/d7X3Tfcu7/90G+zXmTwgU1wnqJ9T4jEH//SYC6A9GAoAZ5gCAMkYDWExmCpDaRlav4MZGeUZiwiYAm0YTCIYSwEdQFWbCCAYHh6YXAMAh3OqHYOaQxMxmszEVzDJGMTlUy2ODDwQX6YHDIGNBhLAiSXMCAcwCKgoC1aDZRZMKCswAFDAoQUzMfSowUKlLgEMwMCjFoAMsFsxoBTA4pMIh9MgqoE4ESBoIA4VAICqRKFsaEELu//uyxOYDpi1nDE/zboTbNeFB/vCgFl1ejoJEIgDg5IhUBMHS7NGBFYZU68QwDGGiYYXATdBoYgwPGDCIoe9qAJcCVTiA4Hxd/Eo0CwgrJD4Ok+zv5d38RganrOVkwh5Z2ct2Y5QfNzrZH+oJ/K9EMeUG8bn/+Vzd3+42+Zb5zLHt3X/nTY1s+X7Fv91rvMKtHjc1T6zs3N873HXNU++85+7V/9Uu7n////6jff7MTlyTVQgAAPBgEwBCYBeAtGAlAMZgIYKsYGcJEmduz5J49fpkyjxiyDhiCGRhsnxsSSpn2GkPlAGGB4+GX/YGZAuGjBxiQAYiAGPMZmzqCjtVIwsDV8VIs6EZUQGg4xAZULObTjExF6CgNSCC9cDgcRBZdUqggFADIzQvaTAAyBMZCxwdMPpsMMnhQDKkuXlZ5WkaGJQIKscFnCQ46Sgp4S/VrHARC4wE5ZFWcV00jjIQFxmtP8pmu2QtpjFlbQwQT2kb3yt5Xv7+EvoWu36XF0Idqya1YluN2ksPEqCKvzKpY7XML9amoc/x3a5lyvl2tc3X1Tfy/jzOvX5W7zLOxa/dW1nS63zHDvNZcy73et7w+vr/3y//2v7z///+5Qf/0F+5sCgGRgLAECYIqBPGCXBJphb4r4eStz7GUlhjhhHwAwYDGBUhwJwYFCBoGJQgjpmIII4BxgyE5kQL56b6ZzgHY6hhjCYQ4KoYEhkscw8TQkHJYBcYEMw8JI1dBccAkODFWAwHA80WB8GAoEA+OACYARmC5RGHApJQBBCEDWEwVrMuUjXDEOEAsAGARBireY6NmPCpMIgYpNKCDXQM0FGJRcSK//uyxOCBo/GvEM/3ZQUnteDB/u1oTCRQwkhAgMskrFjMR8yFzNUJxJAJgIs+VQgAsjJQoJCADCAEeHDmwYoJkJ6xhgRDglUblOWOgIoWB1bL1GUy1tAkaTOtfqEw860omY9DTmJgQzNSJ7pTIGzx+4rDGXen6spxl8lr0OWtY4Y/lvlimx5WrbptUuGV37lvl/DHPV3H8an1b2srOWvvU+Wvzy7rus9zGv/lXL91cMf////lT+8/drG5Pf/9SjAqAHEmADDA/AKkwfcA6MQCDSz8g2VU7BgODJPBNMXALgwVhCDCDKnM2sc4wZwqhIEYwEAODB/DbMkRrsxoxFTNJhMmoM0EXAaEDLKNFgyXdMaCcdAoB2Rt0wPQFggEBMtoTmYIGwKGpYBBggSgWGHOx8VlkxaAgQCxwUgYQmAQgYcMSEYcMx0GA9BhUGA4KgoDA4XmFGcNEcxcExIUAgKNOMaiQwuCAqC4iYWAIVQoGGosGyYJCIDmHwEYlE6xAoICgJAABGFRCPQ4uoul7kJyAdWFK1HhGYsCIwyEUeCYDplII2zRSte+Hrct58bqwcgGg+pcorV55Lt1qL7YTV+UzOXJ3eedz7HML9+5lnjytlutrPf5U13tzdfGxzKlv/yxhc+/jq1nduZc+7//9nmFnkRnSJ/rJw1//5UiADjArgABZ5g7gJMYdiHEn25NWJ4pk0mUQGuYioo5gphEmF0VWYrgWhgDhThgJIYEgYHIRRlwKTGTGCEIi6ZQdowETDKNDhwBkMPAokC4CK5gb3BYOAoHA0RJNmDgQcWHwQHBIlgIAIqGBVcdNGoOLJjgHEorMPDA//uyxNqD54F7Bg/7hQTPr2DB/3CgzmYDKYGMAA8FC1TMwaoTNqODiWXiDhMDgoY1MA0rDFAALoNhRDMuAAwoKTAwEdQu8YLR4kWxwCI3qprTMGEZLQRgBCwtWMDEIRyQd5pC6CAFsFiDYAaAgaDDIYAYZBAkE14p/0luX24QyB3YAjiwjxMESRi8akbfU1G+sfZG+rkyaW3mxXLVqxU1WrTWvsWu9z3Vu169Sc1ZqcpMOdr59r5z+902vx/OxZyv58vZa1zHn//P+v3kf///04BAABzWvEYAWAMmAgAFhgNoFaYKQFLGnQrPh7ouBl6MJhsLxhEGgIHU3iFAyUCBQEZA0wQC4z7iYzGD4xgwMKJi4xgoIAlktkXjMBBCYLFYI1oIR5elBKlWauPoLocaNhoNIBsyKgSw1rrKyEvVuSJQpXeVAsMtCIArMsLohc3ewiBGmoTUVEPV0dhNoQDJEJpmNcuxYRg7EYJj8CjAq7Ush1TB2GgMTd502AkAOGBD0QOyRjyZLYYfn6O7Ek8ovBK8p1Th7pE/cDQNKn+gqAF8pdxhrK9VuLJXo1FhtaCHghppDhRqLw84jeQLKYjDcFuG4+dm1A8Nyt+5uV1ZfG5fF79yORCXzM3MzNBhGJzK5TTUoiEQjF+xhYqSzXPt8v9QJASzASQHQwCkAlMCyCCjBXRcU1ZDcvM/swExGh6DCvDhMKcKswvBZjMKDJMTUDcwDwMTAlAAMDYHkxn0kTFiBhMHkoxKVgMFBEAjIINAxWaUQgRDsYtCxsgMFAGToXIWuNPHgDAl51By8SCQ5yDTCIwQ8LcmDRAYqShhIFAYEl2x//uyxNGApDV9FO/3ZQSxLuFB/3CgYdmMiEbmGpcgHB8gA5hULmEi6YjBRaktYrAqcx6EEFi7JZALAEKAEaNQBBRQCVUGcGEBskWIhOXqT+JRqYMACKSGjOICLfNYvs6WQleYmAqxC7DuLNf1qcrikJkUeptwzXgOKrMm7didnZmntSl16v0VJEZ+jl2NftTVTO/a3T9prmGVfer9+1WpMatfD6+8rNi9zDDeefML2uWed39apc5zDu/rBB3////SMBVAJDADAJUwAADmMByCQzAfxcoyUjlMOz8+MDWTMWjmFhcMN46Mdi5NbgcEgjBAeGFo8nIGxm6o2mSUKFSyMA0VBZlkFBwrGQEMgIEAQxq8TYwnW0Dge9wAAxntRg4UKAu/B5h8WnKQQTJwIAL6GCAmZHGZQIy+JdNa5htEGUxeYcADOUQhAHDDx+MMigWFhYB9hZxiQEAAMptLCS8RCYiRbisRctth0ToARUAAkCJwlQRkRMftLJwU4S+rfPbCZcQAAiDqT5bdS+KwRE8ZNnZs7/PVFIaDOUymG5H+6tRqczf1NRLLOr3WN6zc7yrU7Xu7+33HvKv7/8u/lrn/zmWOWXfx3lciRdFnu/6DANAGcwBsBeMD+AjzBfwKgwk4ThOS9+PzkoPtM98M0wTQdRoDowoxVDR5AOMWsKIwrgkjAiAIMFEGAw1mHjHbCAMao8x8QyoLDFwWMSHsxSMzBQyMPBoWFhirgk10MEhcwuCBCEiEJmSk4AhGIggYUDRhQDGPjmDzMYdDJhIZCysMBCcx0CTBAlMSAcLgYxAHDCx8OZi8xGEBgPEwcMag0xuqjGQe//uyxNmD4bFXCg/3hQzULODB/3CgBQJFAWMg9DYcAaRhjYJpvmLiEIDMZ3AJMGmwSF+TBAsBIKfQwGA1FzA4hATELiQYzpK1jVt8pQnC8AYMlmKnUvlzxTlic7rX7rvHXX5Ldy/UIZ3WszbZIgyjtPe3nQbvUMuvcz1KaOvqzX1Y+1SYcr3PzqXq/LfKtvLlvXfu16le3SVb2f/X+xVPf/5T//66AB1jACQAswF4BcMCvASzBSAUIwrUeFNf0HdjOrxU0wdAEXMdU89+6TW8KP2pkzQ9zFYKM2gsEnA+fiDC49N8LDRRQYCDBZwMDTNCY0Y6MoIjdiQymbM6WTLA0xkrVtEiIwFdJsQKBRVQxI+NrUzLV01VPNHgzLV8zUZNXGyI4EJgND6+wUVGZgoFJUAZjoCl+KipENGVg5hYWDjcwkjXeLDSPQYPJfGRkxEHvW152neZcqaTzy5S0rmKZRqwxJyrMuf5dUimEEylzxRebsasb7SzE3LIFdFptDKJFEasdvRSHolAr47qRrPlWtveWH44ZY5fVsY/lVyu2s/v5/njzG9n2/lveNy39yvu9ftXr/6p9X+YZ/nn//++6ww+7/HmAmDMYP4ipgUDcGHKOabSR2J1C6aHz/O8arKEhopm9GQgBoYzYNw0FqYVogBjAi9GMaKgYsIlhhDhjGHSLAYigSJgkBqmIQEiYMgZ5sCAatCnQQprl6Y63hwuYn2mtHZ4EabMlnNH52EKd9qnpapy4YceuGnoxkZoYcDmgR5uxeZYJniXJzswbzIGwqhwqwY+HGdjgCNwuMmnEJh6MaaiGRkRkJgAgtWwwwjEnERE//uyxOcDo+2JCE/zZsSwNR9B7aY4Y0/mIgCeQNAmYg4vXQ1FsZfZnpfRgL/MXRGT7XrBD4Q3Ib0ExRkqfsqoX+l0LgSxYNnFRTOQFCI6djBp41skQWAlFkl2pRgdwnSbNrTNQ7GD2KTlUZnk0uhwmRWslBColdkVIhWZ8GVu11KVY7OwavfdQTpv/fC/UIf//uRVABCVFDBgrTEtPDJg2jH0dDwIXzZ9CjIECjEVaDL4NTDY5AIRBgSEIQVIhB0eR8wVHALgGYLC4Y/nOYgj8Y2DWYiByAjJMFwFMdxWMOSEMIwAMWBOMJwGFQYNnGAs4yqswwE0wU2YVAYdJGVZ4cpEhBi1YVTGWbALaY8sZUcxAdJGBBGjEA5aSAACOEhQUEp3FYJW9MJW1oLPS+qxVBkETctUUGMqZespYy7mqqYqRfqKMAZDSxiOwmgTIhKumhPo+L22J4sSLTVmRIB9ncaDwbxErIPdFtRXCORxY2uigTn9Zkcihho2HjiIsGxRq7BlVs6hT6RTR4gsLqSZD6tqQKafxTDCT2iVOLiG8b6yFIhPKnl0KN87Yh4Jw7cJRjm9gLDMAicaNBsZEMEZFECYLqQb8/oYkG4Yri6YzHmZGjEaLksZIFCZMhCZWhaYtA4YGCuYEBKZlAmYMhcYAE0YOHSZjmMYxHGYbACYOgAY+hsccwA4pr/6rzdmDRLAw+ZKEHDTUgzaMytAB2hjhRhmIKoHJQGRumsFQKTCCheLDSYChuTPS/CsbUoaeIKgy3BdVii42dPGk8iYw1rw4JguVJlMuQDMpT5hT/JXpuL9bow1mbMGlUscodRRmMMxuXtL//uyxPADJDG++E7pNUyzuF6F3TJwemkFQknih5IcWH8/BoOB4fpy07GqLxTX+SR1L5UISc6P11TZG6dLaMI0BDXyWTE/SMHS5vl77EJmMzpo/W0ck/VeaVUDsRl8Hrj2jKc/PTuHcTRvvWN22E23VYWEK9DxWSj9df56A5RaotrTVXLKAZAhCORkCaxqaPJsqCRjmaJttzZmMWJpaMhlAMxlMiZnaIJiAJhkKKhjQLZjkCgEBImEIySPUBJeYNCSJG4a+m0b1AYQeZBsYUIaNkOaDZLDNCAFFM8LIiwFMGPGCMELQS64gEBBQGHk/gcXMgLZOIQZh0Sul3IRIBy7INBMmRRTEMKJCAogAqVJrtjR6TopaRYpkATOKZPdeQwFQTJ4P0lS4Q4DSFpX8S+cS+0R4Jc7bWYbemhplMrERl5+hlw4TlRGeFwrE1PY0OTuGim5KmhKajLaYZHB/VednQ/yhskgSTcTkR8gYdyhVo4t2GiZ4N8SOrV2Rnq9dHWMmB4arEaV4wOXUY8GRunsjU5G4P6grGz6gObmr4/Es5K5eTGWJUdrLI3Wnl+H0A8YTAYPjYVczcYHDtnITLBeDTbmjPsZzV04zJ42zAkoTFhADDtazOE3TIFAQx5AoEpiABRiiLwsd5iWCBjuKhjOhR745ghR5YJwUxrUAhZmATJ1GaLGpTGaFGwfpvAhYzVa5hHYNvGKNmJAlZAwB0xQsFAm9CoJyS+4QsS7b5rapi0YCLBCRyZcSBgSAi5ZpR1kKkC4S5q0Nwyv5LeDniT1a8hHALR7UORHNXLGqOGnoeiKceGmf91ntXiaqoHoHS+tJZGC//uyxPeDJWG+9E7pkczKOF4F3TI48umZ4SBDs++UlC87Ul6pisPj0IzuzxUH0f7rTEsD4PISoRbiiHtIwaFSg8mzKbT49OrGLA9rdWnIkUQx/J49WFShYelM9KbRyhCWSB6E99UPJXL4knRYY0txHjV0ZqYNOLVKdpciNjAqrXF9DGD6AURBSSeMPWU+jQDdziMUBAwzbzQiBNapMyIpDK5XNdq8WeBjc+mbBuCBObiDxhANmIhGYoQhixJGcSAZwAwKXg6BwKA3IMRAwEDsxOYRwLl7VfCsQ8EX7AQwOzAowhdaSFbFhVBiQQqoAKoHGoXAUUeEQ2Yl8fUqEqVrmgGY4LkixwBBVSNBl3VSsIgF0oMe13oEWtD6jkw+9C5s3bllmq9jsQ5G2j23Hjcvmq8AvoOJXTm116/xJPmnimTQ4JyvkE4jBsdD7EpQRDiWmphxsZiQTSeXCvAtTHQetl47MngkhYaiM0jqL7rik48SC0ZjihDsWPvQ1ukM4h5K9FRyI5IFbB4XTNwxENeOtT5eWiqPJynLUCaNxb0exOtXcy9nopg4QDBMXDJQ6TkNZT/uiTsR8jVpUjJ4UjAYzzOtqTReGTFBjzS5EzQkBjChSTMkZDGoCACYZiEHBmiD4YQZkSHBgUP5hGEJj0KxicABhOAIYB5isQ5kwjRk4DQYCRrRAKQmCPERkeDg6OcNEDL5jjpq67IzdwzqqTDBDImyEGrWULy/TFQFYXaSgw4xZUOCgJQ1mClbOEl2MIWKzgIU7zqwdL2eTDM6Zr8oirkLEcZo0Bu/B0NXHGb5W5G9pj6tfn6jT9rohDrOm8StNC5D//uyxPeDJFnC9G5llUUaOB2F3TKxMnjqQ20R3mFLodV9X0cqGy+dA1jVgxGsfzcRgEg0WhUFKUcAsBEfLAqHJ8A8RC8NIlFI+dIi8bkg3LS84MDm4aoLKo6K4nXIINV2s0eQjtaibEJxgkFY0WXLS4RxLO1BiDeCrEQKRFgrBVGqMQaB/A+eiIttvYfHiESqAlBAKejODcOuMszxAzrT0MurYx+TDdCqK10b3FIlOTcpHNNAAZVhpUdnfwIZcBptNOGiSkYZcRgsOGRQQbe7AMMOdAzF3kwZKJig3UoNyAR0VMGFzBBQUQxYFFhQwcZHAgxErMoCU3zEwQEkZjiQaogHagoZXmsZhkggDDMwA6A0y+8jBxIYaFmKAokDQK67rt3UTW68bImOSlpGDpRB9Gbwe+lE/VKtnqp6Ww7D/s4wlTwOxLIDhyExV+GljQqjHSMSi9GXgzKA/FaI/ef4lq0o5kglXXqRoTlUsGBiIJ0Ii60af72g09TLC0SiQyVj1cVxxYTXQ7xllWcnicpLqJmH2nim4tb5mJqImRnq/omUJDbO6LW+JEBzJf69bF1Uhk0soyotiaPj/T6sp0QWHRxEsASLnv80faJZizMmuTgFzMZGSYHBRnMcHCQ+YZYhtdWmGwQZwSYsqjEKNMcizQfY3yuOKQTVRE7HXOEXDJxUzVhBhgY5TiWGXaMsCxhcJkYhAzBhozkfMCBwKBgJIFhcQgCpjAGk509PNjjWSs4lgOKHBEHip2VlJWCP8qUhAjABYDEr/IdIaUsRrAxm74EJCYFEQIPBLvMgiqqrUnak7UX/euC4TZOfq0BITU5g8dk+//uyxPGDpb3C8k5tkcR9N16BzbH55PE85VrTyp5MBf+TEICtenDmPK0lGiEUDxh05wU6X3njwrG61c7d9M2toyiWnULLAwgbRI0TTifnrMsNq+TTCXWErDtjgsefsHR56TVVFybYaMqFzZ3csLqNmqli7UTMEoeoV4LtO3eBRVUZD8wtJky8RYyg5E6XX43GbozCV4xPG0zZIAyiAAy9HAyPHkzxEsyUTcwCGgwQGMxtEMwsN02LEUUVQyQFMyZJE9pjNupzJag7lMOnKTKEg4X6OQQAgGEtYRrQllGICRhRscofGGmBlokFDow4GMLGzBU01M9Ho0BuxsN8bLOm8EggFzGig0trS+RGJg9xC0asMww9QQGCg4AixVZEIZAgwBBxG+EAuEjlGWHyqVuKxSWyYdSusUC2EQiiH5XEN4PV7odPUM054BNADp6gWKyGDdCHA/Gaw3aeHReBxAw6dIJISjjc7GtUarkRdKZfHuTNhUPMbZYDNOWlpZjVuxrBKPESdg7aJZypQlD59xmYqsOnjgrNOE83fUFdhytIUZPSDymVWMy2mV8oXMlKN5RAuK9kRTdsrYrKEkA0wLAk2VDU2MmozyOUwoCswmbg25JQwKB8zqK4zkPk0rZM0YHoyOO0x1FAx3OYyrScSHwyUHAaicywRQwkDoxjHA0VAEyyOc0RFIBURlSKdu8mLRx4VUAhMyy6MGJhkUBA+Rg4FYzNy8yIyEg0xoUMDRzMzcgXTZ5EzQGNJGDBwgyg3NACDFApl7kJBLQTEaunM3x+E8VY3RNAOYMZCB4gbkYYomz5IswKs6TfIEqX5bEWyGGSbEMl//uyxPmDZx3A8A7tkYzbOF4F3b5YvVi8iTdR8NkqkIxM0NZ3Zx7OZ8o3sZhZVnSo0yubixF/U6Hmi9U8WZHIWxQkPHksvGdtbj5LE4S2ucqVVzAqWt/mI8mgOTW7coqOlgsRpxpbWYWCK56rFg6dRtSMdGaF2FXVfR1dZmV0NyjSLPhRaaiQ3Lbk5K5d1ZH6hgoGACYqlOYEoQdF/6fGJkY9MmYsm2Y8j6aMCYZ7DsZ8r+Y2HsaKGYFbRlGKmaU2Y/uJtQVG08YRJgz3SjSBjJDwdWPRpHKmYBIaBTJgEunCOUFR2Y4TxrooGDJUYJDZhYRAELiTlIieYwW5oMhmHRYYgORiIalYtJhgYpEZjFLGDxIFgUEFlPxKFa3pdKw83O7xRh+DsP1JnaEOEyJjpTFiZA5DxUp4G83OlIa2mdKqVDVKfajYWZDUMV2GdrQ1YiL59sJ1KtWIFka541G5hOFRRoS4a5XkU/D5Zz8OhxVzW5RX0NpWW8mB6OB7tiRaEM2+W15Hw3j6unbCr3Jg1NuLiIr6sMZ547uPEgYedzj7RiteRIGoG2qNfTZqG4vZXKt3JUUYHuHdX0OFWa18TzvACBTZCTNQXs432TQ0RN3SgxShDi19NHnc2SWzN59NZAY5UwTHeuLByNKr4weQDRZMNgScyfMTrv8M0GUx8TzA96O1Es5CKjdTOGESYjiJrRBms1GbbCmOOiDwAagA0nXEhh5cZaomQTQGmjFzE6hsMHBTDysBBqAcBCgkWuATAie0YTce2Jto+MufyIuQ7bdJt+WSQY6rJXJbHUEg9pkNTFuNPFDURcKiiq+ZS7MnuSKM//uyxPCD5fHC8g7x68SLuF5BzbKoSqB4dwjMtIdY1ohrkM7aMC8CyGQx7JhHMmDiz5wOxS9aQRmTWDhcrfawGKPWBFOmCyZtFornh+WSUOyblsNTpVsbu2OSo8oeTwOqPslVoT6llnVTCmFxpl8pJFy7l+wuMKjqt17lI7NWlynt9eaxroL1EQBRhFBWGHKjiaX465lAhhGF0IeYhIUxiRDsmMkGAYGQCZkOBDmCGC+dFLQ9Ezaj2NNxg14hzWTNOA0g2tFjhMOP9vIzRXjXBeMqLc3I3TOaENy5836wQYwjWYNNPr4DXgxQLhQXGRB6YADhhAuGDB2aWHgQHDTJUMHIgz8RQAmCIKkAOAIFAxoTqMJBxBtz1Daw+B1KpuL+wNa5GCN8vwr7gZJBTnMFDR8oaj1G9QhJHGeKgKhAFduMhy6HckiwKA/025n49UkcuyoSq7LonVCk1JFXorhZsPJbPaE3F4JcrjmmTJflc1uSofNra6RzUzQ4cA9MLq8aGnmtWKqI8lsu4cjnRfZVqRQyLtrgfMC25YkJ3CduU6pc2VQZjNzI4Mq8q05p6rNXVkJhWtLhhUMSEc7XWZrY8SRVPArPgwNDgwiOIwVKs4r2M3JjMzhkA06fU4PEQ+YGA7+aY5tZM5NLgxAfghGI03V8RnEauEqaLIQYsF4afFMaSi2ZKEyY8psagA8ZWDsZSjOFyoMvEiM5R+Bg0mWwaGrXxrkKZ6YGrl4UOCAyNDFRIPAp2WAcxI8NmTSJTMNADDwEw4rJosGi6KxgguoMz1mMjizFYDhmRMYo3bc5JiPrBopyp5YRMxJcjNIHoGwMoZit//uyxPYD59HC8A9x68StuF6B3bKwd/W7e5brUUCtbk7T7UDa5RP7GJM/E7VjcQgRfchm4xG4zFb1eblcMS6ELzIPzFCMhqMxwPyu2W9ZhPTDUzkXiRdl6OGVfsjW7GZ9iZay1zqK5Z7E69xpahp47sEyp8nTKja2oTL1ZjgOlEUTEUTi53Zi9xq/MQRtxNU1el1GMCDAgTBzQXEwS4OIHQf8x3Zy6PNm8+jtSDCAytcOeMcqDdzDJAF8wT4AUMJyFJjBYAKIwTIEjMHMAXDBjwIkwnEIVMFTBwzAgrNDhUElc1GUTkrfNXisxwNzCwOBCaMDCozCZxYKGjyMZwFxi4HGKWiGeMwAMjJI+MIgk0/HTlKDMCi4xAOTPJlMLFwwAGwVcMs9A1IKlTZrTFoDXVjsOA44Y8eY9Ob0yYAMBgjyiIkJLQMHdxH9Ow1TwooGhJoV5MYMuTM+Va/abkYJMaYUnSBCCZ5hxpadqTSzAg3XpQoIFh8OUUgs38s71PL862njidNQ08uu0OVBjL86kQwoJZn9rlqxKMbGPO4T+HK1Srcq5y29e/eV+3ui/ed2n+ksdtana16x9q9VqWMa8vt7/lPRY537tJRj1iVOKMpBqJYKuVAwFUDPMCXApjBcQLAwPkDYMFoCwTmj84sx2gKnMGnBWTCQgO8wIQBUMAQAGTCwwcUwAMBqHgTcwJwBdBoFAYR0InGBrgJxgGQF+YAQAhmA9gAYoAziU0MMigxGGTDAeMGBcy67zIRgCo5MlAUxmMlKTTzAMfg4wGRRZPoBSGEm/RMYeH5kYLmCQMY5DQiQpjYAGMBKND8ucBTyHWMU//uyxPADqE18/g/zTwRdryGF/g47CAFCK/UIjGhSARBBR2VpzVvDiugrGYYxMBgcxmIR4YtDsxsw0Eg4EU9NfKogFiSlsBAG7gUADdxIDy8sxFiUFiQzBwSgWklkzb5PDjIUQMGF0IWGzcSDTKjJsZEvG6xAjkSzJiphMmpLCEchyEbFPKtXgIuBUoEKDC4eBxzAgQC8wisBQHANAxS8USPvcmEjxVGbMc4ksw3RbzAQCeMG0VE0swCjBcDzMJ0BUwmwJzAHBoMwdNwyfAjDNS2MQG4xeLTIIAMykkOG5hQQGKwgY4EAA+5ikVgIhGJwitow4FDcZxAIWMRgUQAMiC5kHJmhxACSuDgsWeEjMZIcgsGAcUzBoNLgkJrNeCwwYFiqBGdmAwcYRPxioVP2HA2GCEThQRCIIKBLMUdKggMrgFDm91doYOO4YEXn5MhYeIUtEcZ1Ux2HMXjr3toFwCBjY6MM15YjY0CFW6OniGrlP9mftztipPN5dp+wWvSzrHCDKLPLdujr95bnLFveWvsWJROT8/+FTVjmu61exx3nYu7td3n9//z+rrV3eO7+fM6bLVh/7v//8sYCgAOmAUgEpgyAAeYFyDRmJrAKB+s5z4dhxIBkQigmEoBWYbQpxg1mwmGqNMYG4Jhg3gWmBgDAYRAcpiotjmMgEmYINRkk/GLAmZBEpnEOmSQeKBoxACTNQRKtvNwhkxQCkhQ4DhQjmzF8JDwsCotUjsYk0JMBTDgBMNh1eJhINmlxWIBEFxQxpaBioSHNAbIk3WGhcJmQ02ZYB4CEzTGIF3TMQPCofcYu2tcwoWjKYGZzCpl2Ag6t//uwxPID5W17CA/7hQS1L2EB/3CgfkVV/x0pGKQPGdwGudcbQ4Eaao+qkYqA6I0v3TLHXBGs7csncbUomIAgWXyb81E4lNVKj4wzQbty9YO9GL1akuUtf/pJzVi9dx79ytdvWbO7dutU/5Zhjbp61TP8L2GeeX/b/LGzubxl9rPmFW7T13////9FMB0AUjApgIgwQ8EBMCUBxDD7xd0/DrdLOwEuMy0iQjHVDjMAcDMxRhezRKBTMTcOMwbgKDCIAnMM0MszYDcyJmIzi6zD6JMGGwxCJzaQ3MCkgw0FjECDMehAy0kQ21J7gwJAQKCMEGb1iJDwxcCTCYjMPBYwppTdwlVMTK4DB2LGsDmY3L5jMYmDgUYAAJhpmGPimYbABgAPoClHzGTZM9hcZBL4FAFJAECnmjo04wEDQgHGEEEEJdXc1IIqZPBDJpXlKxCNAUy4lFJYXoKgJZvEJmiGAIAgenFDjrPAIwuxTWV27CpT2DpqHH8l8mp5O3ZtIrK60yqOauS+XOJJ5f9Du5ep69FOZWK9vV6rdrWPsbvz2rNf+41LlP3dFewq53OW7t+99jHlBhnXzrc39PdmsLv9v//+kwFgB0MB7AlTApQHYwJMF/MKAFyjePenw00C6DA1FHMMYNAwfgqjBLEcNCYAYxpgLFnGBSBqYHoTRhXMFGFWDAYABplormKw8Y0GxiURtKEYRMRCeKDMeKP0BAGRBIKgRlJgxeCwZEAHYg9BgOGm+gcpyYGF5QNxwIGRVQAQSjkYGAQ0IjDZWN/h8MBRgIFmGQcg8YWSwOTz2MiL3BQDGHg0CgE5wCDhMAgIeFNy2Ej/+7LE9APnEXsGD/uFBGetYUH/cKBqOULHGVbp9IThpdsGhD0LuIQBWon6aMjePCdazLYdeJ6aGxjjRzsPTVapGIctWL9d95b/LrwIl361uMs+nMOfZ+m3vHXcvxx1l+Gtctfjv8N7xw/uO8sv7/Ody5j+eX71/e33JJK////9CkxBTUUzLjk5LjWqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqowHYA9MCNANDASAGEwHwFCMD7GwTDkvzkwk88wPKQwcFcHCqZVSAZ9H+arge2YwxA4xSA86dRw5MFAxkujApuDA+FwGZnBpgIOCQHfUwCBzGWEMaihmquAgVl6jASvMGgoGAMUAKUQEdIDDrI0f0PEGTGa7MGiIwgEGPv6YZP5tMRGOwGIwMmclWDGAYeBgsBZGLBpTYx0F1UF5NeVwMmYMBhdd+GdxsBIaOzkuf0cC4cwqNjkAdUDh+LYwMMgUMEgKCclf5ganUDy+phS1pZT3KR9m8zmbl2MWPmsUnFrWM9WGRyG33X/vn97+//v73v8e/n/cM991nhzDH9cwzwzy3f1r/19z8tXrTAOwEQwCoB1CoD8YD8ChmBsjBhtIXEoa7JvxiNDSmCKBCYIwCZhTkdGUWJ+YrAIICAiJAJDAnCPMERd0wLwjzI4PAIOMZB8wUGTEAeEhQDh0AQUGEYxHZjVAoBQLMDBQSBxQRDLqMHAOghHQSHA4w8mTnAYMEgEvgh1VjMjIQx4PQgAEQEUGMEIEzcQDBgKAIGVyYCBJiEamRAGhwVZAYWApl0FuQ+rBS9gqOjEAEaFLEd1ggEYUh11o3rCBccgo/ROljiO633/+7LE6IPhQWsKD/eFBJUwoUH/cKBxRZ26jTBImodoJpFBSoDH1f6EwfGoEjctp5Y+7UbcusS/5fUq4KpRmEV9W3dzqUu+///u//8+pvLdj98w7n+GX7wu93r/3veOXMvrcs9+9/da5//9j/////sf///7KjQFMznGOw2TwcwwxgWVPyP7pTL2A3Ewu8G0MAOAEjAHAEowCMG3MXxBFDBwwI4wAIBIAgAqYB2AJGH9A1Bhj4B2Y9Y5UQ4QGwcaTQBTMbBwwSCDHQeApGMgzw8IMUJQGD5boxWPjaTTMKjRG8ED4waBTGKPPyB4SDwME5hQHCAImtzoCoEVQMYaGYNEBgEHnjguFg6hkLAFI4wbMQUoDBACRASWJhYY6KyRb/GEAmYvCo4HjIwCZK3EwqAWCGVQQYHAy/S6TBAaTzAoMXzLuEAJMIiJ3V+q6QEmDwAYVB4VDaCJMxcCfAAAbwQy9EmTPVbDUF1HKVpftz5yHnJjjfvJWVkJhDHJukf6GMLNZ6svws27uGs7tNdnJfO3L17G7h361XKpnS2qWpf5naz+7y/hqrllr9Vfzqb/eqf///5+pD+sPs//+052MOSNTlyo7KJMN5BJj9FkVwywcBQMM8AiDBGwOkwIcCfMA5CQzC7wPYwFYDLMAYAIDAFwB8wBoDMMErHVDBDgNIy0cjFQfMLi8ZABoclg4DiQmEQwBgQMutE6kAA4JgQAGBwEMh81auE6wwHmCwAqqJHA88LHQMHhswQBjAwfCinBSMMWg4wuFAKIxASjXxhDAcsd1hADQg6AJxiwtYrXMJhQxsMR4ImBg8peYVBSd4GVDJUO7bL/+7LE/4Po6YUEDf+DRMus4MG/8GhomXAGiqqskeKAEZJYYgW+l0+rKgFmZHmnuKhsxyDA4Mr6ZuqmiGkLqLy2Prhl03RUy8XkprUvgFOqbnZfef8WBMklOMw7eMus1r3blLrdnWsquu50mdWb3lXvfvl+mz5+PLmOr39wwz1a7X5rDevuh0oBg/Zd+Tf//8tVJQEowIUA7MEcALDBqQFUw3IQ+PobiVjK/gu4wwsDPM1kOMtDYMLcXOqm+M/CUMBwxBQGGNwsnmOtnYgsmVFUYZOhjIjhBrMPAwMIC7zDIUMHAoyD6TWgpLsu6h+pcbUQpQAUACZyRYqXD0wbCg9R5AANMEkMx5AiUOmFgLdCgdMQmQ4eLxGJkiw4Dv2Y8chlcLAYCEQBMCAMaBwKVQcTmat3MIAkwaLQEmbZABVLxUEhiTKAW0khCJd8sEszMBWaTF8UAQcDaaLRWWp+mDABEE3Vai6iTrLYPpuzrnxHGtk77NbmExKFg9P5R31ZWc0NPfvQLLpuvXpdXKt6v+WW8Oa7fu36fufLH3dZU/dY8/+cxy/n3/x1U1h/d/vWX93l3Cx/9/+///////96p2GHf//QBgCIwCcCEMDJAjzBdgZQwlsZZO0A8sTIcRDkwRQIGMC1BJzAhQJswV4CNMSsAzzBQwKEOAezAEABwwD0EDMHoGyTBfwJ0xZJMLiCYPAYCQ0Hj9KAIWYIwTAQaGB0BmEoms8GQHiwKAQz9ExBOqOBAKAJg8YRrMMw0SZgMA5gQDxhILpkuQKYJgWBgNDAw0AEOPM01AowBBckBJvwqEBrbQDMGLCmCFiMGGJjlDh0Wk//+7LE8QPmPaMGD/eGxTo0YMH+6egFg5hARg8YdFbYEBEWwYFA4Fv4gOEwYKTnPsDJjjvyseDpuL17LJKFSBtCoJEpgPg7w0FdeD+1asYhySPhZUPVp62aigpmzlPDDMVZ+/sXkUal0sgWzHLOFBNWbOd+1OVL+c3N9tZTcjo7tLelGq+7mF6k+ek9+xTXbtXLdq7R518bFBet3stXrG61rPfP////////3qaitx93fKHP/SowAUBIEAEOYFYBjGBkg05gOwycaEnxeHymhGmpImTxuGTwKGObMHjA+muQfGAoKpgmJokHDHEG/YJGAI1mDQjmB4KGBARAonyIEQ4MQIEI0Fpg0gJneAA0BgwA67AsCHdFphwAtyVw8INoH/BmAIs9KwHEJvBKWtMYChCBjA0YM3mWGhiAUEAC6E9wrTmVAICLFBzAwUuwSD4gIGCqCIARCsoGI+DAMmMkICnZV0OI2omoNAqcLe5tjW2vuEw/L3iCwIBQkaAVsoEnbQ8d6e789el83HZt6Ydt0U7RS2MWJVAVKjnTYyqXU9WU2aa5ljjVs2fxsztLewmprDPV+ens6e7ncpNXrFLRXqlDVq47rWr9NqxWprVrWN61rf/je/XP////////1cpXlx1////////8coi0MBKAMyECEMCIAfTAdAWowR4U/M0PxSTki/TJ9gjKQZyIxzEZgjVsmTQsNDAUAQELZicOBsX/RrsShgjEYYzGAgYJFTCy4RBZbcEBoUBTOi4fzwoCEAWmsDg46kHeYRgEvVYBLgjFTCQtI8BAJkAQZetLcBwqxEcJBwjO4CkbXzQGGIgRkiWHHQL/+7LE34OmmcEKD/dlxMY4IYn+7KCBWdAUDT/MbDAYEAYHRCYgVS8oCki1dpGKWmLAK7kEgYKO+BDYzIBLxNelagqZlloFdZSnYOKygCDAdULV1DH4x1qYi0tahH5Y2XGW012NvpLo3K68+JC1HSPtI33eaVWYzNxGZm39ls47MNRqmiUNRKNS6VWb1nG9jjyvhrDlnW//PD//K/awx3vlXHWO+f//9zn//////////3LNzHf////////1qKowBsAQMAkAKzAtQDgwd4BAMKjDbzWEoNAzV0HRMNOBBjCEwXUwQcCzMD+B2DClQCEwOICHMA2AHjAPwC4wCQB5MC9CwTB9gBQdAdjAWQAowCYANJACwy4TBQCYiaFs0JoFoBNTMOEDLwQEApa804iFCMGiBf8CjhobAYuylB2X6EjkoPjEh9dxCOgILKwcwkONKZULE4CIUHi0xtIM3BICGBBjYsAgIVRXb1mcdFiUaJmXNjV8hiYWEGCBIOBUhX8AoQTAbTWc6xfr2RLGVuRvSgf0KALQZIu6Z/pYjMJEBKEIoD7oaYSY8bCUeg8ekdaq2Z20Y3U86aafc5zjVRXSefN9SC31ZZr+it/9e0bI3/9TxgwAwAuMBpBDzAOwmgwZUGHMTcIUjRlTB4w/kCrMTJAhTEKgzQwIYJQMgRdNVwVMqEuMbSjMajsMH1XMeFHOGCLBVgYienXNxycOYFQGgpJwTgarrmXTgFfDlQs2aWNFxwrSGJK5jtoYjImioRo4AYSqmU/hikedCDGxKZkNkbRWnepBsJUAD801oN2MRaPMuGzFTAedTNTIwYQMfeQKcGBDYgL/+7LE2wPiacEMD+zxxHcjYEH+7RFDMTkYTFeIYGABxhYugsKnwEBAMZqcrMGAAwIeEg1FtTylgWB0D20hiGICkzAnYkTrPU2i2H+lkKpJZT4W85RXmpI/FWOXrGWssN/dqX8Nfzdjnfubs7y/dTX/21mVFVTQAhJEDGH//ga+2pj1Grbf8rxpzDFX7///44gAEGZuYbHiVFSNrKpMjZiNugyMUCZOOKtN4BBM0SnKElMGBVMSSWKB2MEioMhSKImVM+AmMGAzDiOMZRmMaxvCA4MQwYMYRFMFwTKAKJg7MPCTMNAiIiCBrs2RsC1DNpDCtRCZNJHBggQLhJ+cwYFxglWMpLUzNUzNQhAg424wEAwclIAQ8KASYwIMSKA0UBiSQ4COggcZUg1giLJwpUJPGJBGCNowlngwKXaU+9DNgKEXirmErGjKFSCVxHWfGBIkng5UqZHJ3Hz4VEaCESFtYAp1CS4qrHUKR3XIulqOoJNzNRZTKpIqgjZSTbgFIn1VeqTQ7oJ+blz/zfHXzxChXZXEM7aFCWJ5JdzCUrTJWzzl0oNNOkyyi9bdWZs9QKEwDQLjAqDXMfIK8yHDZDMRE0NSUqA1eVDjjDOqbozuLDsiYGUCYgDRoJRGzDyaFJhoEjnLCYZYrBRFPVGB6XNMCBVsBL+QCBkoSaCJGSGRjqgZSAGPnBhoGBpQQhZliMl4YgJGqoxgoYYEQmOwREoAEEMoKwUkggbEACo2IQssyKAjXkbzCQotCWqdciAC3AkBI+JDMoTiSlZcYcAFBcj0vx+HrUWJgdxGwOKmstBW2XuCmM+kXoWnNFcFozhObCYZWlj/+7LE8YNj7aL8Tuk1TN24HsXubKFQS1mMmjczH5TqZrVZiYlFJbwt3O2tw9KpbOatWpRfwyq/F+PDQcmLPK9n5iDabdJl+EWqzty3jl3l2pUwk/ZFSxekry+Uxu/qXS6S081eqfPXpnksnpT27DMJobE5MSy7uWV7PbEpwr3LXJy7f1vlq5X2IkwCEAA7xuRGBygZAmx1Xqg4pGh7mY3HhRfTM6LMJmwy+BDCYeHjySjIy0VjDwVMQDslAIWBoECRh0LgQFAIYXMNqoCIIBS75kijqL7qyjKCqg6CMgLqHQEwxEOX/Y2Y4KEwuAyUuGoKlKRICIFO1oDeJgv0tVurqt1V8rt5JGsscHdEWBgdql+VoZL+mWisQLzByT5NwfNwXyY6ihCZfH2czbQazcMGQy+QrVB0jWpCcXLOsldIZQtInaqlz6FAZHmGC9EsJ9ypdxJVUpeRZaGiYtUUCccNeUztbBfavQKWrsurmnRFXuxPOFVy8CKr2racuDFldVPiUxXn+F6xSQUKJshuHahbnN0GAu5sAgcmDGLoYpaDhoyh9mKILiY5ZjhjQiSGNYHuY2gJhhwArmKMGEYDgMQQGIYawX5gsAgmKqFYYJ4OpgYhGGCmDwYFwRAhCnMP8GI2oI3oI5bAwGE4Z0aeHWimLEi2w4ZtGs25Iw4QMpIziwExRIwSZrKMiLpiDhWQU2AAJE5KMMDix8uWBhKEh1XCM8HXCnOqdWsMKMxeMkEpmOyvKCY0tBw0vE9EAjktaSGQ5tblzqPolWWmEjjK2VrwWMl+3RAk1WXxRnaFBeNAMn4fDhcNVRYjUWHohri0eH5NeXn/+7LE9IEhKaMFLmWR5Pq4XsntMjho6LcMmwfJDtIyJEDatEDeVjaE+UUQ8Ccgp2btrD87P05w1GDg6XQoj5OuZzEkRKFw4l19JI4OOiSCES47JKtxSPIkqeIw7iskBKks6hls/MBKD1yCjiV3GGl8Du0O6xAMAcEkxND4DIHbAOe1U46f9I89qsx6bUzRS81RP4bN01mVUziKg3aT0wFG4wrnoypSczHUMwUKMyNIgwAaIw/H0KBCca8DrUa4jDgYzQwQrNh5jGDALF5rh8Y4PmQlZrUYCQozcoLbmRkxlYmYiymenjloRA4EMMEVg0UgKKKXiRSHCr9MBVgBAEAhsBAbywCWqCBEug+0fGAVOYDADcqidLJ7xgYWpJ9GbDwSim5DX0GQwWfoECiw6QbyvUrGvaGUwLr3QyzlUb4LHnpuUthcWZZXQvfLoRK39lyiUthDyPlZhu4umW23BnXueuEwRS2nlj8bYK7ESm6d2Yq3mcYybWN2qdmDNtWoCryF+aBWmkgaLRSQz0su8ru7ORbLtVy5a99mVyGSxF/OVn8paaNQzG6aG7kuruF2tRPVD1K07G5O52Y9HqlyUP9ciUHUz9TcYzdAwoQgzGyArNZUzgy5AYjGDAaMT0cEw0hiTGBJiMOUMoxbRZDBgC8MOSTJac057WENkwDCh42BrM8cgdOGLg5soqci1mKiwyODTAYuSmlsZkQkWfMbCzAA0wQXMSUDBg8wUIAQGKDYOIDASExY1dULkKHQXMWNFAijdC5JgPMLQGSU42jQOMnKfEudBxIASUQ9JIWXw0lw3F0L0TQpzvUARs0ANoTMwSICKXn/+7LE/4NqccTsL3djhKc4nkHtvXBCVoTIwixE4SUJfYS2oYqZYdnBVM0ZsZ0nNMqkcn3jOwMjK5NabfpuRxfH6dKLV77cezOeCSfscCG8UNmpyVKwzwGRlWq2r7MjPDgsaqVEWL7ZhNkWLZsYXmeqYcVtt1N4qxOyaq5xtzQWqZHw7uLbPJEbaMkemorcqJJd2h7VMEBLMhTMPwGOMuUDMrQ/N0SoNVzkMAAMNVTVMxzDMXUBMpD4MVkPMQjwMbkZMaB8MZQgMLQqCxyGPgWGJQcGBAQmDBemZYiGAYADILGvLgwufI+BoQAFhUageb0mRIEoTGiASEQ7GCanWCF1guFBycQETIBFIrrBAYLhkRUnXRX/JmgzUXnW9jlpyn+fuExFxK1BJ4S19drazamzojgcMRKduRM06pSIxEH/eiKu5S0D+OhCL1OFDZhCPCCjeLEdyQWjgeRsIKIL3zlonHg6n8cIZ1XlaIfFflRcV2i0Gh2+hWaODlV3qj9QiWZMNIze7FSlZuy1/Up7qSXXGu+qbGkp0v9WiYPDt9ijti6uLC9edxLIVqowccU3eKRxkVUe3dQEKIRMDgZMKyXPX2PPix9OsBxM60xM0UDMUiTNZQLGERMvBdMkQ2MyS8MawyMAhVMczBMGTzMSxeMoQgMlhKMig8MPA6MRgyMigMSidUMKMoOaQMEcNgMIsoBDGJiG5lmWCgUWKBR0aCnYHGGiJBYOCnwiJBUGX8McAFChfR2FnSp/KdeCAROkyIkWApFjwFXKvwoPGRQVDOvA0Av/EhECb59pe2dgyHpMJUUepKFcid4cdVFImsORRxtE2Mv/+7LE74MkMcLyDumThLa4Xs3dMnDs1tx51CfH2FylnjozEggloEzo6J3kPDha+dL9J69wSz497ubqyeGic7NztCJBu6IGIycgdQsElmpDIkB0YPoy6dEFCjKpPs69ErKa5KS6LGoj1wzuumUDzlHVY+VhzcubsPW2BHMMD14qt1Zbn9XxqjALAaMUAg8wTwJDZDFRMVIQ8wGCdjEPCPMCAbkyIw6jBSDsBgNRjiiLGixiY1eJsNNHLzkZcg5rcmmQBCYAvpnIlnSCoegX5nIOGJQcFR+DjGaNJJnJpmTAgDigaXiwYeTDQHMMEYAAoiDpiUbEoINSAkzaZCJqGIg+ZoBxhsbAIplQGAQappAoSEwSoWWsThlRE5AnhjBQzyLyM9OEkZzJFfXnAupDgl5rCwH+GkkwRoyxSUKIShYZp9DwczwuplyfidbHrAlDIQSBrO3JxItJcjwT5iqM4D0UyJXLmptLsgzab6IaC8HOly/KWI9dRmlxQtPsqlV7ikX0JCHt3+JFynYqhfYgxmZ04M2IuUNrCpJCtChsM8JXJ9vkxLFdq5WwXqoUjL2ZqZFVmjZCXKug1c5sx4DyzFGeOeqUjtrS0aMA0AowsRajCsSvMXockxOxATH5BvMNkFQwexSDEUEcMSwc8w2hCzBzAwMlbTQ14wSaPSXDcFI4EZOKVTFxUsCQOGTRH075VNNeRVJNFLBAWGTkZM1moFpVFDBEkxYCCwSjMYCEAI3EQ4aDNApvBTYDWIx5lDlUyMZEIUisjU3ECBDby+BFiLkhaGifLB/oKECfONDz9Po9i2EAjEpG+GQT4CkTwA9IGYkgXxr/+7LE9oPoMcTwD3HrxMA4XkHtvXhK1UIs408aB0lxSTAh6wjVahyjofSdhImaA7bT6fH28NJDG963TLsuZKzIV7EqXrdC8nbliEhjaxQiaoxPMhok4Vrasq505v7OkJT81JWMu8KrcwQ3rm5bpbfjR4UJ9LeRSu11ZzhRNta2zVZY1YMrpU0iQHjnafTi7YM4hVfXzFmjvnlKMCh9HovMLR9Nf5MMREaMXRGAwEmtL1GzzAmuwMGw40GER/gZzwxmjIk4TP4OCQ0hJzxCCpjONgQI4VDwyZDQxjBgCA0YDAEYyHq7NPPDLSI1YHMxGAAbmghowQl3zHAQYFgMCHUMJpA6amaGsqhtLEFQkI3TDwJStqRECigixeCXIgJ9mhtfVWdld8eZYiY4DWVBGYxCkl8NqAlUhX+0JC8VB5Mul/X8LXO8kHKqGAI661Z1ONrB0N1L8HPnJWrVIDjOdDVlzbw9A9l1X9fR037YgVoBrRH5bEc4IATr95hssQeWDwjDAcEEG/CQamZs+XiyeHwNsVkVbsQlPnBy3HGeOmbi5Qtie5lCaVJWE9TvHrMQUQrNNuvJVxdWN2sjsuxm7J4lz5depdDiFAiNEmEBDMiNcd9RltIhzkMtHASLBo0FlCKM2FkyOXTUgDMZlQyINDFR/MLioycIDIQzMEB0w8ADFYvV0JTAKgIGB4EgREEACGJaCEQykQChwiLQsQnlACki3AjEPFMwETEFBUK1hGIBVHwe9OlJR568bqCipMWmi/zTGsQqJFt0qUvg4x9oixFQFhC718BwUrViJCUJKXDJHaWlQpmxkIPjvFLUulPMDXDH5N3/+7LE7IMlncDyDu2TzD21X43MsnGHi7ZlfKNQenLkRrJ5zsLxs/bCySj6ziHAymfpHeF9EnocLyJd7Vp+XExUutLVF13zuCz8GvHDC+Jy7GocMUUFoy8tulTVQzC7QtQjsSz8wtdcycnwN2TyA/qgcupkWKcMGdaqA6AhAAiYDZIpiSGtml0WUZS4bhimiHmFUGQYsoOpi6B7mCIBcbVtmMCAhhDYzA9JEN9pzPT03A3NUJAqQngzBkVgfcIGcGxK2GMBYjiMLCgg0pc2wQzBA5lMFFCIEYkOhLABhlAiICq0VOCqcdknDGmFLiwceJLfWY1MigxyHXJFQhgwqVqPS2HNDgqPxcFO0wgsINKgZErhS2IQyYYWmaFgKg6YIQCfdmKWUhUtCgNy1N0oqdR4LC46MCx5A7zBKR+Z6TSmGJRYhNmX09anj9SUTrswXKJE/8ES15c4y9Ekn5PQYVrV27NTVeHpbXg7OHZmpLJuxL5a/8Zls5Wlkp7S5u/zGau8rV6fusZFMyupE3omL09MSCQS18n37DEYlNmjeeai1DDNq3ZeaUQLO9tQ1UrdqUtHVq1c6C/LNbotig3K4BAcweN03+kkxin0z/GYw4Jwy+HAyFAwy0BsALWY7h8YKikYbAoEDEYqj+ZhjiZNhGGA8YGhwFgRMFzAM3gjEjyMVyWMegeMaRNMKLQ0Ei0qGqhgQ5yT5jwI0jVIyFqaSxlg5nyJZg2QY8D02aoFYhZgn2pczNLe86sTdrr7Lupqd2Zx9yEZIS+z6qz0jXVRwHEFnrgd+BETkj1VXdXVG32deMP7AzfNMeCq4DXZyCKWVm2Dw6n/+7LE/QEoJcL0T29JBHq2n1ndMnHKpCKhoV3TmMmDuCY8sLVdYzI+XpU68twromzRNGrcSktaw4tUHy+6CrdVn50eGyszabWXST++5TqZZ4w5DsvE9E6Z4uPDxoqpy4SlZcVmRNLZMEhqFMkPj9HdBJSHlb2n6r6szD4wNAcyccQ7XLA/8ZAx6rU2iG8x9NQyVVQzvcMx9SEz1HI13Vsz6AYygeMxuQoxrTgySIgxcLAAAOGLSYWjEY+JOaRDGZIA4Yhhua1lKdqEgQGN4HDKFgAGpj5UbJ/GTIAOfQsFgkBEAgYYaGPOZoCYVRI5EgNIODW4ooBAIFFtEN0LjHA6GakNz6S68XaZIX3HgqTpxNKAgA1GNBAeYgJDQA5UQgtkajaYhjAAuAeGGdlsmlRNvFAxUaMiDGmvI6i8HqdNRpXj3v9LS4D/JUf62WaRX0PQlDbIUwtCDUd1Ed0YxFyaLA7VL1JsBRngwsqkjKx8o4yIOVfZ1MhzEf6vYiRGWcZ+0XC4iF/eqlcpZncG9cLu0KZ8yrMiRbXFsVtfPvDi1waKPWtN08XFXmnqWZHT9Wyw3eE0p7Vlni6gn4oF11Mx5BBAhGFBhqFRgPOpm9WhwgWxwkCRgkdRjUKZrkn5qgppnoZplyXxi6fRgiX5jkqhlAZJjaHpkIRhhWHRp+ZRgoYYWNA10WNDeDBKAwweNCQC/Zkr0ZoSDVuDAsy4xOPLDEzEI80qAqIGBmYUBgNukgsYWNGmAwQ0A4vDAMt8zRI1Fd3F1y91Gfy6o6j+I1LQL9FgVEiciPmIDgyYiLCxC+7yNObuwhRMCg4cCCowmY9bJYH/+7LE/AMoucDwDu3zhN84HsndvjgYk1gwk6AAnD8Awa+j4lQdEYM4jRJJAiYB9HioFwn4jx0SNNvoiGrLYjtKSCfCoU7jJiHqkjSr9ODfWLlnX1c/VsdWRTcWH7G2s0WvZmZxaozkwKE4JV3S9muu40slTmUh5J1Vw2n3ZYMey5c4dnlv/7tyndn68lVMdtYGqfUbzf97fevmeiQBGoRoYqQJ4flmBbsdpKpr8PHG2mMVEz7lTLUqNoPE1mojCLvNFuQ24sDRpmNSHI5IqQC8DCpkNaCk1WczNLCMbDczCSzIlUxUTC4QBugyUbBBUdSDmxI4k/hjQnWYoFDxGYaUCpeSBpgx0YUDGHkAHBzRjIQkYCDhwQASQYEEM8cNPBMna0n+Q8YcDB5uIMLCI4Bo+NDa1ACVmUA1FZbi7T/vqYCLqtFgsDAAKHGyoIIoocUBwsJRutDCSrN3ta1Scjk87Rf1tWRPbXna8afW9DT9xymmZ25jjVGkUJR9Tqj9IjLhsvUnBUHQ7FR9HsDxdaTnvJID8kmR20f4b3qsXWo8maP6mKJL8M5V45dvHKHVCgluNYy10zM8YS5GXXEWJJ+au7AZcRDAJLjdFAmYhE5kbEnNQEbHIwGjQMNBpYaGT0SCQ0NQMwuczEYfMbk4yKEAwvGMDaZkHxlAHmUjOAAUYlDBggBipKMDkoGlgWc5CFwMOAMJR0CnpaW/NZ0eYXK7ZplrSD5VOnlCAEJTMTtYMNcvqzdI81hA5V1HrkUZo71BEoiDQZcBQC7oWNIl36JERZWBPmYafxORN+LJaoOPsrp3X4ET4iRZaz6ba0hxiA4FEo7/+7LE7AElMaj2Dm2TxG60YF3MsrC/scg2BkyWdSuk3D6dMMUUviNK/rX60icFyIjeIB8waHI7m6TrK+fTJYzgrGjDkMZGHwrB7LJ+WYj4uuki/r17B48fKIXHTk7RtoiVK7UAdSYdjvhTbKpBXnNFxcL7AkHk4hdYthIhnR/kay/11QAEIxAQTYlfPs5c7IgTQdSNWBMxCnDTT+OuxE1RZTd09NdjIyIzjVZCM2hU2WvzPjJMak8wUGzCCQLfHF7kakQJvAumj26ZmYojGBiAjmZ5cYuEIcYzIwQBRFMMiMAAUxEYDCoMM4AcwWLzHaAAQRMTDowqQzMpJBhfBBiXkOBCYMfUsNYxg6yUsmDQZLoqz1GkKQsfKgoVkMBAozf0QFiR8MuvTAQELALBndNBwo0a/qioGgd9/01AwZXDivGhwLrWmWsokWE+IzUDzAUAy4iHq3mctUf5QtscfgORS98ncfZiLZI2ORgLEwKFFW2yO58dNF0ckjr7LJTVD+Ww2Kp40O5wwaoIEylL6EsWnsZXYO4mXyd6mR8DFYOR0EpIVkssD0SUw7HBiRSaJLgiWJJ+V/KQguKwLCcVlykSVqh3b/VBP6XlGsZ94FGXMAgoVS5z1sHfw8ZXNpnBFAZlmlC4YfMBn4NGg34btLRkACGTx6YpRpkwCA5UmYDuYzIgccDEhEHTwYMIhbgw4EDOwgL+mFYG7uj1tJEHCjAIFhQgSIxYClFVIYO2Z4aRDhisIk4wJMkDDgxlADkIptgCwJDQiAUN+IxiMyyFOsSCEumimVBBj1b8HuutZ33WhaOSHAwJEvKhoh2L/rmHhqluCg3/+7DE+AMpMcD0TmWZBJO2n4nNJnlAogtRxEjCIDVbK0apXp1bFak+kAI0OfONxqecOC85iD4GrYS6vB8djYbIz5IgL41IpY3JGXIRhVdtUZC5E0IsTEgLLolCSJh6ObyQkKrhojDciHZuCtpIyBMooOiQlYOmkZdkUGCU2hYcMWWTPgMKiApRpGNi022PUcdIkWSqBRRjAUCTRNBzInfTN4rjTwNzFwMyoCJkQNRiGrhoeK5jODhp4EJo8PpiyTJkoUBhmLZhSoRg2Qxl+X5jIEhhkAxjyTBpWapqUDRkYP5gMIpk54Oq4wGmnhZpAMYiUGBJ5MfGFLhrSKZALAoJMvG2bGCCQzIAg6MKMzDAMoAwcAhQPBA4IwkWLzKgUvTdyEAAtZnFSDo0XeehVcUBU/HFYa1mWAADUyZiVgRAFF+l1CR2uUFFRg4MkayaPN1MIAxoBSmSxb57VmN0Z5NOHGoRCE0ka1kxuAbd+KvI7Uug+JwzGYfqTMGuoRiehV9RG+pUML1cCdgLTJOTTxMOjChOLR8Gs6iP1tny82SS7APaBDWCjyg9LRWZxto7mIqJDlLYcqiEYLlJCEYmJ+PD9cRXiOtSp1pPQjgwogRPn0crZd5B1z0kAIwIME5h5VGBlmdqq5hRmhCGAwbMFxY5mUjWxMNKpg1AZzfABCqOMujw1KMwybGgjgYQQiW5kwQhUnGgjqZcKIYMTSSLMMYBhgwJMOxGFOjIIlNK2GevmkTDQdnBIrGt5jgpkzhqz4CWjo1IOVMvIqjNX8Lu0ndLynKaA5qmfKKPw0BDrWomRPGuqLyp5U58ygWslfKQjI33Z//7ssTvAShtvPZO7ZPENzRfmc0mec0wwYVoDaOHQysdG25VLLkWuxyKr7LpN2d5/JW48HyW9GmsSiHorDVWfkkFI4yNIYRkVWNyQyVNGuNHWSTpNK6UkkSMNHKOIROQaKGzCMumK5nV18bm5AtZo6DFbaCFQ9VuLp1bWUoj1v6TTb0cZIyNy8fVAwQQAMJhgephclx099xjasxmgL5hcPxtYE5o+CJpsAZtWhxkimBl2O5gmAZkydxn2P5rQWBxcFJjsIBjCdJkEMpgSB5kIGpjcERnGNAIB8w1CcGg6YtoaYwg6YGgQOkBgDWLIpt5OGJYq2BYcAqkbiHmJuAyCHNg5hgEVEVJpPQcBDPAdBIKHgOOnPw4uYFB1pBMBgdBlQeMlwzKhkDQxMBO0w5lL6MHYskkKALgix+X6T4MRCDKgRoBIGNABQSDgFdkNIVywYCYU3R7YAk/vGhZoB8vcORTi5AOgg1VluFvSi6P03SaoWvmqoVYjkUaRzIawqBldI6AkT+cm5GGTVgVaHzvY6bOBWD6SyvPWGH8ULDFYWVHWUYty7RbwuSngxE7OpFRs/EiXUpFFrSpS9XHaWVaYw8jTOTnHbV08jrmEjHj+OnIKne+kzrLJ83vDdvNggFg+aElJmE7nE2SZaCxnFBGYEkYJKpkAxmJxeDjYaEPhi5xnJ2cbIcphAamSw8bZfZxArGbAqZWA5l9cGkgSZMThnVUCIcmnGiEecA4accluYkqMjhpmDrhCDMOMi5QOMGWFCKTB9Uw8gauNAF0vRJbKK1PB9j7kafykdike2Qt1C4BA6mlLSorAcZ0+iCJQJqb9ydOkv/7ssT1AyplxPJO7fVEKjhfRc0mcPTMJvNdWlTqwsqZ870Jb2NUFBap6UsLkZ8mgy1BxBMU3ExSopRrkdmW0aWuaRFlUhxtFIlRDCBDtI0MSpKwaPtkQVUIlmmTzTmQ4KaAfaSR7s04qg+qSRztXOLS0ZW5pOVtoZs3TSGOJJrxWybc8nCdN5S6AcbICIgCMuA+NfgGPePJNWEJNYCMMjhNNrT8M6WfNfknMUjTFBSMEzINGh/MeglMhELMyFfAgLmAQCGBI2GaJbmKaFGLoZmMhlmPwVgYTBCQQ4GBhSEBg0ACG5gHYORiscDcAUSChRQsoCiB0EgwufDJgqrB0QtUYEAQFTEk0UzEJYgglgSLpuIVF5AYKJgSwQKPL1JQQjBIPBhZoTAy4ikEI3YSOZlAT9rAmCKywLjTNCACsNAIkgqEhyocA7G6wIopx+iwRbHojzWQQ8kczouG4OBoM65XPOFcbeq1vhq9eZXNXOSFKzL5/HdSPY0YnKMR8qclQpro1HU0qVDlwsrmVEvT8o6gp9heQSdIpgplXQpUMZwbEJCX7esx4yNeNU9nSrRLFAXEGJ4TyFphfxm9hVtYUDNYeK773SVEDAACohGjl4GGBuGvLnHtrQmfTXmgqlm/J4GSErGu5FiiTmRA3mx60mTMAGEyxnMxYmPQtml0lmUY/iM+AwcDF9PDTorTCdQDBYZTA4QDYBc6HoNgTSsLKhYEEIXCzPAsVHTAQow5kNAFzPQsFDZjRkKApgaUd4XGFBYGEAsCl1zEA5a4wCo1LDw0/4SYFuBREcJ2FqG6QUW8KpDhbDIQgn5XC3k9KAh5gE5H6P/7ssT1Aye9uvZu6fUNDzheCd2+WAygcTnMouKgJWPSPcTwdcND0OOY9jpUSpiOC2QZGoaR1VEjHr8mDUeCOXCvZnA6kS1GKrXEz0oxKNPHSpDn62nka9VKZUKKVakWUc9dNbjdlTyhZV1GFChzXx0qQg9jkNdrICIiTFTvIzQ8rImIcz5niKNiYXu6ubYyTKrDDOxwIzazSNzdF7BNHywQp2eK2TPZZG6K2SOdCUAAoGBhEMxjYDhnTapk0OJjSMZm0PZlqn5gktRkYWhnwYxiCDZi8h5nmlphcAYNGceK4eXoy0WAwrOsyWBowUOE7VKOGHjDgkwAGMZFDPwwwqkJgUwUXMCBkARcYBBgkHGDmAXEQcMGGoZWkKOGLFRnoyAgEWBUNkw14u47AgCEfraYDpUcVoGvxKHI4wyKRpczh0QghCh0exBCoflokkxog2EBaNyWcrblY+MVJbK56tLLyOkcbBASxrh4N0io4LfqSbxZWdy2FcPR2W3C4hrzjD95w7XMKVbC3aO6uH9JGU8bd6jbCafJp7Ze6rt84xtI67Fd5xD/n5gnb7tY4bTR+rtpveGnasX6/HZ8dssF6BCoIBhTB7GEuFgZKyExhOAzKbGEUGY7VZpCMmYSQZdF5qQFGVyIabABlk7nHBkZCORikTmLxuaPQJmwpGfTuadGRn1gGZB0FwWaJEZi0CA0XtXMGAleoQ0vwlo0YwkZdQiKZ4ewUNWayArSVapAadIhb6CRiK1GcuSwttmsEQHALJIA1Uw40lSQaYhKZUvMvRVcxwi9b3LHZMqmr1pM28EAM8iLvxh95XAjU3Rh2AIEfKhitP/7ssTjAyIFtvhO7ZFMvzgeye5guNLopD1uHY7QVJJSQ7Xk0xXm4/cfqls1otRyOL3Judp787FID3u/Fp2USuP/ceWMZu/AFyQPxGu3Z+lmL9y5NQ/2US6YoaaOTUnorNm7JcKa3qlqxSI26l6GJ6S19QVE4lTTc9bn5a8EtjkfhmUVpRUt4b+Z3Ux32/u0MCEGAxASVjLhHzNAWdE7xg8x9HAyYRY6iSg8PdAxdek29cQ1JPAxzFM6gfw6fQwxRO8zgJc18bwzARs2RGww9pQ4JYQycX4wIHMzyDYyTKc131NtCTHu02+nN6HTOVcoeDRhMx0EZoUBoGHy+SHAoECAHMPBhCDCIBYWiKhrF1qMKHAVTzVovBTsTjOU7WIrAwwobIFQuw2WGFqMUdphUCprv+oe05Uj8vJATRm4oZKuj0y0mMs5geDoMllqO4Oy7UuTCeGOs/deu2dej7MmyWPATtvKxqbikPQp+I8tmUO827LmszrPWZx6mnZuWzsnXnAMvZxOMNfxwX9dmncKTu9JGXdvNaeO9TMif6vFurmQ4qAxGE1tVJB8Vt4wZEbcWzjt67jPYa66r+2ZfVjMixfqFzlSWSGEy6vWfamp5qU0cak0/PwqMWa3AZSuMLh/MaT/My6OObxAMbB1JkBMnDeMuUgMtRnAxNmdYamWRJGJIzGMhbGL4emJQkGJpWhwjGhB9GLxgmKIXmetpkD0dieiJHByKIEYx6oCw+YMSg4eEASlYXaMAB1wpAylpAOFkz1bTBAJWKCEmnjYW+Eqc6EYsEit2TQA5sOtbkih1JIXig6RxyG5+A33bR+pa2HOUuzBEP/7ssTyA2lJwuwPd2PEAbgfCd2mMOik+aAOMF2zc2RsSnrZOkUgzagWHw8WFIHieWFyYkERypqlWGYjaFRhCRsMLIyhuRAKE55PW204mqfiHdMMPl7qDsYmzlqb8Ux+QimvJyfSiz260zVLEFT/QLJt612SbCJrsyThHs0YASCyYFhAxo2GCmf6haYCBJxiWEFGMmXUZBych4YPxjOdRp0wpuU3Bh5uxwMdxmGJhlCXZjMx5ozGpheTZkieZjTCpkaXJlBQxy0wpx2Y5tu05jsbho2RZm6bZjoBBhoBpmDighl5BYYyUhEgjKhGRJAMgNGCFwSIPJLpTOl8NI8Q7Vd1sLV3HVI0hrdhmthfrugQJpDPVgmsvo6KymFM6ZvD67C1dh+1BIxKp9gzNoOYfuUQe60YdFka/lLqjJ2YQy4DL4g1+OvfLJVGYm3jTozDU83V6oAdn2QuVFJbQyp3oaZRGGR7aW0OAobZJDUvsZcqv/S0kKsOZDTzyiPRqrFuRiGLcIrSlpmotIMovSTU9T51pHaormM1WjsBymmvRSj1Txa/+EzFpNGoYl1FPXpdG60NV45FpPfiFmRTmd2IWZuLSwwMAszCvG0M3EkU2sDKDVC/TVpWzZZZQdiZoWzRuaKxkUTRwEVxplChibCJjuR56hEg+3mqJWZbixzUOGesGe0aZtJbGfvgb8qRtwhmWFWaFKZxRdmDR6BAcYPERdgZBQYHuKGp9RBhZgULEAxDBkAQQPBFNMeBF1XkjdJoD+tq/0Bs2dWIu9LICZpF5bDVpuEdYdJGhQfDrTH1a+1iBHhfqFMQfhcxMDo3ixNna7W9l//7ssT7g2jJwu4vdyeE2rheAe7wYEKvwincB1G8vyupK3BeCzSPpm6lLE5G9E9LHLhqakMadGUuDG+Qezh54hYh6KQ3ZfV2XBbvEoIq508Pza54cbg/8PSOejNB385qCsoYjkmwhh37OUtlMvy1T2akqvTtJ9BYmqlbVyVzNfGvl9WUz89h9rUvvy6ramLtBdlFWtcpvpZdPRO2EAwBQejLAHIMUNSIyGRfzLLBSMDcIQwag3jDEI+MYkN4iCoNXS7MrEFMElONjG+Mqx2M9yGNXDoMhAkNOA1MqlVMszJOPF0NtjqNaTvMwjHMChCMLQtMERCMeS0MCwYMFwnMPQxYuFgHReV0k6ggb1fpgQBZhAAKKagqHEQcaqTIc8GEbRuIdOh4wzwJFBM9CxaWIuw4HqBWyYHU0nWoEqhyiSJcjsZTJRCkOsK5ArhCFYyncai0fCoTKoY2s/oaRhs801k9OaSYUSmTjg2ne+bk3Oz0RDG0uy+sjxIpWqq0vRGIwFtTnkllh25qE23yEK9QQbRHuYjcf7UxNlYzmjtwvldv5oL5PwN5gt0OHK1PIjpma76jOtNTkyw4jhFeWducZ1BonYrS+keR6sV9xbED/IxgEkH3U0eECZglAhxcMRrEQNg0IvgUtTvV/MJj0xblzCCSOdscLg0zieTVrZNgoo18MDBxpBVoNLDUyKjTAFHMQAMeKRmTaY5meaVZkgQkrVUUipe7MXQ5xoQgU/YbUsR32WtbM/o0MTCp1zt1b6WIlPvAqvskyFQqZK6p2xLceFnCespdd/VSxNL+eZe5DtqZXnvlk1qSW5RuErojM9K2c4WHrP/7ssTsASYVwvIvdenEQLgfGc0mcYRMSHBQF8Iy4aLiIG4g+cGxOWJ+3SQaJ0C4VHTMe4WZXjIRlYN0etsmOoQYRiYaKD8YJJgGNHkVKEiBAUXD5MtWDJOmjThqKyQ5FEYDwoQCWIGmRkLhuDguKEDyNVy8o6zBuUmm4vkqNtAMAIKkweANzMbRPOBcWkw9x+jEhJbMIUH0whQ0zOcLAMfUigwpx5DCMHeMOUkwyeStjDsA6OBJ80ACjRDHM6LgQxYK5o9emDzEpN/YYzyGDD8EASqABmOePAyOBDBodMng4woFYBQEoks6SpfgFB0wEMDAgDQqUyKAIkYmwvRc7VFuNydZ5GaJdMAazDSLjQQSCCYGqKKvL+MtS4wHatBbBEhlAjTFk8DHCpB3F+gHGZxljHJQT1vRZOJlapieoQXNJCrGYYrwOU60IRJwGO4B9m4zEkMtDUyJsS47hvC5spy0LycNGJHlxIMSBhWm2QuyGEvT48hpkzQJWiknOgh1hFGck14cahWDohIwNsuiMY3NwLcWx+3aPeiumUFHi/FRkJnMk/2ZsQ18wq0/V5UJsxUYhSGRke7UOlt0wtL6SbRy12i1CoE80Kx4hVU7sJDB4QwSShoIPR3ifBs+GRncW4KSUxPP0wW8wycIA10Hs2DGUzhEEzFZQtuaECka4MEYpjiZcmeZmoSZEGQYMjIdHkGiARjL6Ye0C0gAEQ/lYIixdwBVyoHIkr1IgGAAIBJqOGpbD6kVFkGACKNIL3ggGLNlYG5jR3clzfu/FoDdmKsSY63JTlozI7TD6C86bps4flxVNp2ozVQKVRJxI61pZbclhf/7ssT6g2nxxOovce3EiTheCd2yOJpwHXhb/1YvXc8MA6FeFQsnZOHwKgNQpiCjAsTDoqASHmxOJRmqRk8Q161cVCWWB16FMIelmRsWi+XLMCRQjr2xJw+JcByqD4uk0sQPkURYjtbiiyVtbe9Tr15X5fZo6XttxwdQ9SH4qxpXB9DA6xeoOWFcbCf165chz6xqAkACUCgwmBVzT7LCNYIZAznb02gFMywikw/Yk2nWE1HdUzqAg3MUo05Zk4O3kVPAxeEY3FJAHJoZKMAYmn6ZBjAbmpAezAHFvZ0zaaaLiSQxk77LKo2YWTJVG2i5ElmYIq+XJEiIWAWnMKRsMIFQcpCwCjAFw5jzSHpfpt1IRiFMCXskQuWiVVgksioywJQFyZehqonF5l6mIOKqgu1jKM6F6GjzblMapVss5h5tGWsTYVA74OfEF1shvuJNvJK4ciV113TeuQ0rcJEzZpFpljDKz9Vo67Ub5fdNoThs7kMeXrJ2IVHct4u1LbrEH5U9ByO0IituHcZRJ85XL6azAk5OyyW4NGqV5XKoO3QwTQTslnpVUp6l2xSclsAQPbfydfr4/lual8bv0lSJXZRnSat087bfuKSqVWM4pUm7tDwQyBMYOIlZmADeGHwgKYWAEJhpitmKuCGYY4QZhLBkmB+CUa/x50GQm6iSY/5QUXRjEyGtrSYKGBmlzGzGSeFFB5EkGsTsNB0CEwwGCiYQJCGFWcYWCiiZgACgkDDQUMKghZFUwAB59VVgqxigGCwbR9BXjKNxmPRpUZey7G4+LiNkgRfymBQsqgD4TT92xH8k2RWkPL6SpFMRNTLORIOinv/7ssTwg2gBxO5Pd2OEqbheRe49OjQSApxGJdMKtCZFQhpuH4UCcjiTsCFNbDBaS/MShhsKPbVYX0y1o03JJn+xo9YXKlU5+tD1qVr9mMqRNJM92VFO1yymaQljbUJbG6zLBfzqO7k8cHqJmjTvH0sFQv3rG+1GbcxoT60tHTG3Mbg2uTkiW6K9U3a3jyPFV7N8xtNd+zQYLhWC9dO4VTAGBiMXIMcwuRRjCjUaMNEDwwRgZjCSDJMIMXQwfAGTD/AgMkIeUwMRxj9spPQoI3kTTeZCOewg/OSwwsmXS4IgiDEGYPIxqksGEAMYWCRiEDJ6GVTSZCDMpBwDJgajy6C6WWA4hNBsmSB9DjAPYSqE7OQnxilEmGOAfcAni0LAlz6L2wnvMYhrxcuZgk/lJGTMymQ624mqFqw+EsJiQyIpxCEkYyucU0pEadSLVJvaan58kNQ5dqNzcz9SDCilAhcsdXjtdjwEdUSrPNFMphuEM9C9OTap1McyRVKDipRPv2M82eDc/rMD66ecFIazW1E+jq5mh2YmpzVb1kiv2JkhPG1stPFu1wo9Z0jTbHDZ4+U++dsKnorE5GcmWXqRhc2lsZHGAw1V0HEYwTGYy3Qo1f2o6zhE0sJYiOEzRRo3DkYZbgyyIA55TYLKWa2IYdnIsY8nIYeEAZDK8ZojAasEGklxxmsa+8mPBhhzycadhUZGBEwAgNEGQcVEoANBIOPTBQFAaYgPILIlPqmkmTDBCDAkKf4hxlDpVYRZVGQbRPxzjhwP5MOkJJUqXZMVYdp3jkV6MHEWTAWEWlRsx/nWW8ApJsQZ+fSPG4jjgUTOdjOo0v/7ssTqA+VZwvAPcetErbhdwd294Mn6JxSOaKqok5OqzzLqxjCIOj1Kb5ynpOVBysakMg6kipDly3njCU57LbM/UqHIih6KBREGIOXdZRR0rjCaYZJG6dDJ2CR8qqQo7txdGyhdpVChto72Bl1ESrbFTiPguUZCKtzxfdMblvauTTXZncXzawpZSODa3rze21UM9VG5MbOqGlABEA4YrwDZiWgTGgSL6YrAOphEhVmIuKoYuQ3hi5hsmLATuY1oRBhXhFmGqLkYpIOBgZgylQGQw5wbTBcAIMF4D8wHgKjAnAKMC4H82h47F4zoESNmDJgweFQQkAAqUtswMRLETkvkb0DIs7anTYUwmaKxMeQll7y2qWhe5pkUY39SlbaKsep1HWIsCay5yaDbOw0CAWtJ82MGkv1Aipn2cyG0zNPSuUQAXAWGa3B0IlTI2SxNl0gD0kC9DLgko6kwjJ0McChEPL+J4hyLcTJgSFDF0Q5c+oPTQ9MyUWV6YZlRsoH4lsltUVQXZV8XET9NdYiVqH1+n7AnmxmhsH2sMqSZdfiI/ZO2ThqUqi6C8qspdapEWfdgcW+/7scxavdbLyhMwbjIABgAbBiMgpmJIh+LaByoFhowG5le6wVdg3+hs0kBk2RUEzyJYxLRc5ZFgzUAs0YFkxBTMMMowVxNjkzMZY8QIPEcjJdgyFQRQMCGwwQBr+W9MQMlHTCgARl5a1Dih0C4Apmps2BkowBIT1L1Zi+DaKqFnEwFg0Ro+2FLnWF0J6ZAhoRsXBGKMl6JZWQc6hRscfsqTZiZqQx24ux2n4ulIdKPIKk1hDi5RSmQ6IpkPf6OU//7ssTtgyT1wvJPaZHEuzheCd296HjysQdJq5NK5JwVGwrCmJazqE8TpMI1lA7ORnWzdcmUw4bGeq6UrWm1cwNquRqrOxDVcVyXgMbVchbir1bGjPETAiqyOwNr41Ver1K8ncVE1QX1XKdWzKtDWdQyNr2Z/EhTwGZ9NCvAZlptq9gH45vWJshr6KiWbEdmd9UKQAMIz4MSULNfm+MrruMkBQMQzjMVFuMvzsMqEONLBZAiVPRlI38WSMPHWnoYge5vF4GAGiaaQZgRxnyUUZmuplJOGDQKaMFoFFRiYBDIHEZQKACYdFwYELJgYDhBgQYLyQqCksy/LBAsGo+vdIlaDCFgDQA6gCYOIYBMicFcLQbZeV8eYRRli3gnhczDuQ8zk6YB/IYB3L+GwGGNo+EPdq86nFsJW+Lshjo48G8fJc0enlefy+jWOAwm4XlMKU+ZnE9TwU0s1iYtygLqoKKxTNrkvJ4kKw3nMqns7stiTUCuxlMrZ3HUizjeQUNOF7ClbVtXtbdZFTYVLYTZoeQkNvPRgcoakVLU0Zc2941MjjtQzUVnhxsP8N8B1h1GYXGPNAYpmNFvEOu2M0SIqTBZCIMKEvw1shdTDwNuOoGAMqiyMMwDMNKjNFyCPclNNnl4JS/LAFmTIEGV5zGnZcmTqsGG0EGUBRGIaBm75XGBwgmOo5GTaLmNYfGSALBEYMTPXkDOikRqIDCABRCM0JSN69WpBxA8sXsEPB9DlwlOBYJubCFqswW84rQmuSmZX3BKw1VrzAYs+UubusDQN3X4uWMSJk7Wl5SVnEmd1uroPXGn/sLzdB3WgS2CIy19m72R5f/7ssTxA2XBwvBO8enE7bidwe7keOEelE00yGIdaU0zaz33iuDcl/MHlbhvq57kue6MvttozuNQdGHmfaJu+6MC8bPGIakHYEjGFNYbpTtheWJRN5IegH6X4dgCxN1cZXHLTuacGUzdBSSqmoam56A5BzOczpZdZmYtt95vlSWWJ63lAEnjkOztFhVwr0EVlk9Wqxd7X8lEzF56m6oNAAMBIHkxbwVjC7WJMzsxUyVB/TDiBSMFUWMwdAqzBoIcMeERA0WUAKKzIJ7MGpIxFqzXvGMbJg1E5gMvjYJ5NgGsxaZRK3mrpkYNFIGbqICDZlIFp9BQFG5xoAFhgoijrMlcx8cgCijwyGh/en0KQAIQOZAQWfKhkfS0yXIOg6NlpzT2exqDopIXTcl2J2MNo+LwULpPXHovEG8p33gZqrYfcpzqSUv3Bzh0VaDqaN1IrHWJsmp3DhnKMtno49CHrobMMQmkcd/Y7DsRgBrTsXpJDs9hGHLk1uKP1IJc4jMK07DErqRKnna8tsxGlqxrKPzmozB0MU+U5vG3S5UVyan8d2Jy1n21Yry6rXkOFf/nb1i5Z5TS3789NfzGYk/7t18Lk/Xt0v3rFLyXiMEQLMwzEITJJGbOMUh48ZoM5lRkx4bk1yrEDPYfyHGZ0pMb5leZds6ZlV8berMdPmCa+HeZVBSYeriaDASYRBqZvoQbxocaMFGYHl2YYEaLAJwqEaTcAJUTDAAsZiLkxYGCoWPS+ANEQAgGqk5s0oQCRgD4a2oCwmBQw0wwWQhSmgwtf15eUhZq6D4Kga6rhg6UaP0oS2TrXGhycltmFKUrdZ8LBLsUbP/7ssTrA2WlwvJPcwlFSThdhe7seFWTJVoDXAFgqCVDJ9i8JbV0V+zKNrvx10a0KjJCFrfgtNV/2xQIwFicBOzFXQkcSg5krSGatOljeOww1VkXdF/VbIKZ1GFqv/D/HcpWxQ5Sdd+cgeAq9K79M8GfJSzfKTQWiO2qoGywM40Ev3XRndOrEInT4Xu2aLsYmad2sMbdPAUohyo8EpksEyl/ZRLqCu/UplcM0UTnXhv00rv8uPDM0VJUl8MRCerVA6AguBWYEYbZjnHfGi6NKYVITZgpghGDKD+YDwPph2AIGEKJEYTwRhhCBDgWdMF3TR5s5hIP4yCk5N1lw4bPVeTJeYwNoNQBjD4008BY+ELJir+JDZhiUZEMGEhJo8KPYZl62ZwVmknZkIIYIrmPhhoQcCSoSoEx2YDUqBQFSbrhQEFgihwxHGlGsRAuJJS7j0D+QhHi9JakDfOUuwC4I2hzmZAStsXcY6jvU5JCPLRVE0HIW4sLLI/Q5BsEquWFc2yZdYhwcwezx55nuVM1My4jLNHGBG+3zbjMTLc/nau/bIT2HTxFvLY8xZzwn4UHKvn+WyNlqi0UcFks8pLekXMGNqI/YfEbbXeLiXb35bYdVzSvizzzXo9l3aNrdLRFgBGiAxGQzQCuOAPI4Kaz9ZqMqHEw2ITUijNSJUyaoDPyeNrCI2a2jJw7N6Go1mUTWxHM9ncwZIzD4pMpmQxu+zgAFNbk8yqEzGKxMJAMKjo3ogLIKGYABQeBUxUEowXGs1uPg4IGIx1AswnFYzAFsx6BUFFyIQfMJgNSqEIEpnIBm5tiIAYg21+2yonQqOQRCiUIRf/7ssTaAyQJvvpPbevMbLZfjc6yoYBkRXCTqdllDJM25wkRgA/izlvwa+kOp7NotHMcrRv8dpzA3kDKeFw5Xw3TJFZ8XyXrAeqzjH5yypHSrKT4Yt5xRT895yloC/yyFdRUhauXrqUu6XGGcjhWLZgUnKVb11WSXW3HljR4YF8mMwLEpwftQojFiXm0R+en1FjqBpzfvpMrffTftGoQDBgFTI82z9m3j5+pDOopjKwsjdpkTd9PjCMvDQwvzAQDTKlrjU4NTZEJTOktjAEkjCAljAQbTSQYBwhzIFATK1pTLEszEBPTGkFxCM4KRMyBLMw0GMx0GowwKULg+YiAMYxigYiGkZJwQaGiudmZmYYB8MkZLXnBTx0RmZO9mHhIIGTRRYSF7XDASAwgPRavcU7W+8/HwXWAAJD0WAWcvAxJrEmlrZJe12HqbCI00eTFzB4zJgUCUXjcdTMGyMptiWKBUZFEsADAWH4eDjj0cxJSK3JvRUdE42LoksuN+SWTctmTLJ5JgsfEm79RKX4el8lHhUXCUimFaJwkk5aJN4F77SEJROe8hxomiksZOZ1qJa85x43BkCtZCysi9/kzFGGHjy79Hkj9l1SrfeTqYcVAMgIBAIEA3piYh1GqOHoY0Q1pg9AfGNgD2YrIR5g2gqkwyZgcgoBwYxiO7m60qcbKJpODGeiEYaDpj8MnSgiFUaePNBty1me2YPIAyKLTKgqFR8ZeLZo1ImBA6YdFwIBYjEAqJzo0yMFpY0UTTLwyMUCgwGGjQZkIp6ZCDRicDCEEmIgEDgZFJlTpfjr56E5K9m6mFeVYnprD2OUWE/RcifmgJv/7ssTrAyZNwvQu7ZbErjheye49eGWYBIScVRIRGWJJk7JU+UUUeBwHs0HiqzpaTjLJPJQ/T0Ty5k3t70c5q9QsayuqqKr1wY1m+LyNEjc9g7VKct7UyvLEFbzeriu2NvTEJRMHfvbxYcjZuCwTMtJrQnWGqaWM2QZ7VorZ2+kWJeRtdOEO+3m3N41IiJurHiLKx6l/nvV7j+LSsLEARogIwBQAjEmFjMiVtszs2HDLVCWDBVjB2C+MS0BcwiQKjCMBvMEgF8wXQjDDyCWMBAXEaB0MQga0AhdmB+DgRBAmC4DuYTgBJgSgrGLtZpiiCuUEgwOSDViYzlWcIAI40Pw6YQjlhWP+eTcmc5A1FDNCQMkJvAKVVQxsOWDL6CoWUBycGbxMqe612HuxmpOsRn4YUOXkzZt3Oh9XDAHgTRVav8IAleNXbVnkw5q74Ao5ihgpv5bD91gDaSCC4rVKqtYQCu8eIZJHceDOFfLgHDpkQRpQWHHWRTSi94ss+g2Sa5KI1qqLFys5pweONXuP0vD247aIrI3HV7S1J2L1e250nxqOcUvRKXGzM4acJaQTlzRXxsrcma6kS56lIYMrDf+npvaIcCMMDdGYyW2azCG77NQMa0wXwLTEKE4MO0UMyNguDCnCbMIUMQwphZDaakPNRQ0JDTmtVPqJw0+Qjk2TMPKM2KLTBUJONoA1uKDbQDMLiIwCRzBjKMwO8xgJDCRiAxCUvBhgMCr40EoDPdBMsgkxeORItGLwsZ+CZiMTmSRsOiYKD4iS5g4FlAxaYvNYdurzzamMqRkOdyHPcplEqjoVRLGaodQr4KIZgmKcOcMQev/7ssTrAyTZwvhvbZHFFDheAe49eJRtTcTsWgfyqYkLMcmhjsacRSfNe6vT7ccxLTuFnbkm8Qx+cyTYlcpm1iWEmOwLxDFhYX0Ck1Uh6sRk6Ogpw+0wqDfQhAmkspk9zLOhW4VDxjR6ugRRyqw/mKqSLamoyw2xHNQNcaGqHJwmhuTBfbPPDfUTjJZ4+an0WeVtjKZjfN9XceO/YozLFcl05tmn8R6xIxQTaQgMBUAowlwYTMsEONBFgoztQjzByBfMJsMAw2AZDCXDRMFQDMwtQdTADElMPLjKcgwTZMsXzDGc5ZUKqsd9dGWJ5oMQBUU08OP3ZTcX8yspMWBTPYQHI4CN06jPB5gYQ5GegBK1kU8CiYBdBiaXDZmacYeAmPApjZWDSpYAuxDMAu+wqj2u004NSgOpGKE+54CbP5DkYZJ2IkTIBfYDST5MGs/spdJMrSh9yoU6wvL6MS79TMqmkcmVucT0XzMmcVdESUVwYXj+joWo1SqPFzVtGBynrvLaxPIXiyObIt3lYWzNvm8LECe22+sDG6WraTU8elXkaLe2oG4W6u9+BDpqNuPDxv/EWt8429pC9aUntSe95ps+RcAQIEKYT56hqrmZHwz4kd35ycVqeb4GYYU6UYtTsZrmKZqEWaxmAYqxkbdjaaDIAZroWcOmaVDBMBwuMqTRNwyIM0A7M6kqMQhIMso8MYELNvsE1+RzlqQMtrwx4GjI4KFTCY3JhigxlQsGI5iHIox+SAQiTCAaMJgA1gQzC4FMQgQwUnDYhnJg2YkGgOEDnhYAL/nsIBa+xSUojNQWGGQCCAMWwaanW1i3G1E5sgBiIv/7sMTkAyLpvvgvbevNSbheBe7weAsOmUy1hUqgONKJJnPy+avnDkcpVDB8Xik9TuJKYavN1kLyxeMt9PrxuxhxoxOwZAsjaS+sSetDGWrKtQFTTDlUe4/L5fBTwUEfvZWaWmp33bjE5JYnc5XF3zf2JS+xemMJTfwxiNN2hrQxDMohdpoMOdxj0Eb1NXr8qikVj8xAUCRS1T6eOgpJBIZqZnLMVjEC25f3cooNy/dBjrtazTSawgxMFB/Mu7SMFcsM6ttOSCiMIEuMKiSMWi1MmCDMPQSMABjMJxCMWxvMekTFQxMfTXMkhoM9QuNNFTJt86gRAIUdmfGiIhuGUaG8HjqRqp0bYEmWoxFCmNooKLgKBCXMBgkxcfMMBTLB4mhzBwY1wuO5dx76C4IYRTHSl50YeKkxMQqUM0qc/juzqZDryCPMRYATAMngSCHYgR9HuKgEBhcHBklcyLuJORVpIGa80AU6CxfeTruPV5Obu602tr7HR1dxevVqDhj0EuO4Qv09yBhaumFw5qpM8e55m7+VWLH7odoLY3nUv/3zp1yH2fammPTR2O9lk0ohXxl+uQMWmF/vybP3O5hmPabT60cjfmC4PphLBjGgaQEbOVsZyJk7mXiHcYGJFJkQCnGGqMsZFpLJ0vAmqpYYcrBm+WnIACftPhuukGs5WaTXJh4QmtCYJAg0WmwqOjF9KMiB4ykfwUgTY8WMugQ6pTBqeGEhQYMFhg6xG7EwazSZkoMGGk4bTCJghDG9hcaHkho1NGIB0ZnAGplpsIiYicgqoSSM3EwMD0mDGk6ILLdOvPLBCMEYiRFIiAmmLSTmY5wZ//uyxN2DIdG+/C7tj805OF5B7m04B4AUOHAdgLqCIIGgmIvA15/eMyYLMvdPFAFE2sNpEK8OQ7LIelC9I9A7oMwken5lzgP5ekcJgWOyyglTzt7PfI6mbX5a877S+H5JMQ5SSt4blPIW2lNLZnqanblIp25Vy/CvqYnJXPaiMzFMI3Z5Xs3ty7GPVZfSas08ovYyHtSlv7ppiX5SrOemrkoq2rVJFq1SUdnpy9KMaK1blE/cqW5yAKQVFTMMTDaZWzNjzDZeTjfUvTSwDTL0VDQIQgoJhiQTQNH0xxNswgJ8w2Agy9EAxKUIyHBswAHNZNTyCs1/GMXUDSxoMMQc3mcFJN0mOk6GoKOQd0A9MKhEJDRmBWaoAGJCBgRAY2imgj5qbYZ+DGOkJiAmYOGgULM0ECITU1bmYIAKul+MGROrBNBm/Eabu2ZNyihTsPc80COo36lTK2dmFhxEKv9BonvsaOyorLhctJgApPMXimY45eVJlQtv2XvrYZw/Wmqk/WMs0PKWKTDl3Vm7BVTT75V+uwu0aVusPS3H8EUdZs3N5epSfyDZvMz0Nprzfy7b2GH3P7b/sNW811qDP2/NNZWlfgxUxLA4DKwGqNL9UgxCcbzlECuMgQuYwACzzADGdMokyYaCVMKUdsxoBcDtl7Dgwzz4eXDJ2GjcOxjd2BTH2aDilEQYipj6EprYfBm8PZkqFZpaDRnEZJgiSJnUERt2RwVPgwJEoz3MYzKAI0ZBE0DHYRg+a7hGaIAwaDnWc7MAbynqaKisNRYYqE0aXDcaYjSZ/FSYAjQLD4AQPAoNgUB1xmA4Ri3YBIM5YzCiwOaL//uyxN4DIbnA/k7tj88GuJ3B7uV5pvgmI0c64xAXdASDwIzlz0YgqkEFixzGjMCKITEpMtVdQUCA0Y8UKKGcMUAmaGapb/GMoGXkogMULIJ2mOOBg0/AEIDmxQAziBYALlgI9L8UEMQIMDEQBiEF8BCOZ4JfMxDDGCX8BCDCEVlBIIkGvcEDAIRN8wiAIMw0AggotkQGABQi0gQIDgGZg0EIXTuMIQBAIMGIEnQoGBj0m0MCzCkFKAQMoIXPAS7Ti1BbRfpbgAANZCoJa92i7hbx2QYAXoZiWXLtqJAQBGhRctopYnuW3ZuwwuonQsswAFOEQwEGrouYXYcVIsIAeUuuWjdYtwWscktuXQU7LdobqPFnEkE2y2aSCwZZ9e6igIATMTTQH8H1BAABgIwZamG0qhha+co0gxQNfNgKBmRFpQLGGCZhgOpYY4gweHQmGwbowFcOEogJNZkiQMtIaOQSq5cJXQgDFgXKqA0RHMxjxIItykSYQY6kBsjARKCCzSqS3lhXVgJr1t9WcyceQaohyA8ghKB0piKpsdH1zkm3JJNcJQjJxBJrYgk1CEItJRJLJyJKkrCVGcmKk5JrhKJzZiY0OTGhKJzYknqYxdTGTzJi60YnqYnKkpjEdGMR0ZRnJi4Sj1gyPrnJ7AZLcMj6ExUtGTqYyeZMXUxk6dGUZyYxHRlQ6PrrVvHRlQyPoTF1oyXQGTzJi60ZPNLnkp7zR9GuXXOT2h0qa6/jEjEAHRroEcd5nvKpqs4caqGUkBkYsggMRBGEqdM2fWDguAGEhhcVIVtUjURWBJFIegIJg9/XZaayJUyKz3NKZSkTDkik//uyxKUBoGnFAK3li8PmORmJtj+gkDS2ugJRSgeQKZN9BigTtpiumgFb3OW7dlyYdu0tLDJ619Dp2tCUTl4knpyZCUIxfEVhc8lJROjx7CUj6ZXIZNTKzFSy7OrYnkwJFnTkkg1ULmhyEEmwNkkxEEs5l+OicUwImglREonPLnpsyZXWwGRO1athdZTA2EonIZJV18Xe1e6gxs1rXUF7R7Fzq24uN5q9mfM0dlJ8hocKNhkFQwepamN1NOStL6WEYQKYADCwuNlMQU1FMy45OS41VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVN/ww4zaCItzcDNFQKKhYgs2heXpS+Z7BTKS6wIPC6gXUKqIwcFySyAsOiTC1MguESCl/ER0mB4IDGmWoBISq2ZAg8uHCoSmqvI70ffplL0O+5rjOSypYFjLDGbs1a84L1QXBEGR+MT5lbUJZhEVQHyUVCEaDyNjdQkQhB4YJ2aaQpJpJIzKJVJeE54tNyJCWKnWHx//y//uyxEsD3pXaigyl/UgAADSAAAAEMrhsZRSqeb/5RThN0o1cMknB6FKbKsHsrTjL+4rJw3JYiVUfGmiEqgPoUSbDSFOG5v+Sp72FfLiaQ+R2lAW81C5HqbQKoCRCEiOD1kkKY6WKM2w5oUxVFKSSyk0WrMJMQU1FMy45OS41qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq");
    audio.play();
}
function startTimer() {
  var timer = new Timer();
  timer.start();
  $('#timer').removeClass('hidden');
  timer.addEventListener('secondsUpdated', function (e) {
    var stop_timer = $('#timer').hasClass('hidden');
    if (stop_timer) {
        $('#timer').html('');
        timer.stop();
        timer.reset();
        return;
    }else{
        $('#timer').html(timer.getTimeValues().toString());
    }
  });
}

function stopTimer() {
  $('#timer').addClass('hidden');
    // If Call History Table Exists Reload the container
    // This is to keep the dashboard stats updated
  if ($("#call_history_table").length && $("#dashboard_home_link").length){
      // $("#dashboard_home_link").click();
      console.log("Reload");
  }
}

function startReconnectTimer(start_value) {
  var timer = new Timer();
  timer.start({ precision: 'seconds', countdown: true, startValues: { seconds: start_value } });
  $('#reconnect_timer').removeClass('hidden');
  timer.addEventListener('secondsUpdated', function (e) {
    var stop_timer = $('#reconnect_timer').hasClass('hidden');
    if (stop_timer) {
        $('#reconnect_timer').html('');
        timer.stop();
        timer.reset();
        return;
    }else{
        $('#reconnect_timer').html(timer.getTimeValues().seconds);
    }
  });
}

function stopReconnectTimer() {
  $('#reconnect_timer').addClass('hidden');
  if ($("#call_history_table").length && $("#dashboard_home_link").length){
     //  $("#dashboard_home_link").click();
      console.log("Reload 2");
  }
}

function showNotification(subject, body) {
  Notification.requestPermission(function(result) {
    if (result === 'granted') {
      navigator.serviceWorker.ready.then(function(registration) {
        registration.showNotification(subject, {
          body: body,
          icon: '/static/helpline/images/logo.png',
          vibrate: [200, 100, 200, 100, 200, 100, 200],
          tag: 'helpline-notification'
        });
      });
    }
  });
}

function parseUri(s) {
  if(typeof s === 'object')
    return s;

  var re = /^(sips?):(?:([^\s>:@]+)(?::([^\s@>]+))?@)?([\w\-\.]+)(?::(\d+))?((?:;[^\s=\?>;]+(?:=[^\s?\;]+)?)*)(?:\?(([^\s&=>]+=[^\s&=>]+)(&[^\s&=>]+=[^\s&=>]+)*))?$/;

  var r = re.exec(s);

  if(r) {
    return {
      schema: r[1],
      user: r[2],
      password: r[3],
      host: r[4],
      port: +r[5],
      params: (r[6].match(/([^;=]+)(=([^;=]+))?/g) || [])
        .map(function(s) { return s.split('='); })
        .reduce(function(params, x) { params[x[0]]=x[1] || null; return params;}, {}),
      headers: ((r[7] || '').match(/[^&=]+=[^&=]+/g) || [])
        .map(function(s){ return s.split('=') })
        .reduce(function(params, x) { params[x[0]]=x[1]; return params; }, {})
    }
  }
}

// Ring Tone Audio Enable and Disable
$('#toggleringenabled').unbind('click').bind('click',
  function() {

    ringenabled = !ringenabled;
    if(ringenabled){
      $('#toggleringenabled').html('<i class="fa fa-bell-o"></i>');

    } else {
      $('#toggleringenabled').html('<i class="fa fa-bell-slash-o"></i>');
      incomingAudio.stop();
    }
  });
