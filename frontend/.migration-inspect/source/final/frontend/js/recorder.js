/**
 * MediScribe - Live Microphone & Audio Capture Engine
 * Browser Web APIs: getUserMedia, MediaRecorder, Web Audio Analyser, Web Speech API
 * PEC Techathon 4.0 MVP
 */

window.MediScribe = window.MediScribe || {};

MediScribe.Recorder = {
  stream: null,
  mediaRecorder: null,
  audioContext: null,
  analyser: null,
  sourceNode: null,
  animationFrameId: null,
  speechRecognition: null,

  isRecording: false,
  isPaused: false,
  startTime: null,
  elapsedSeconds: 0,
  timerInterval: null,

  // Callbacks
  onTranscriptChunk: null,
  onStatusChange: null,

  init(callbacks = {}) {
    this.onTranscriptChunk = callbacks.onTranscriptChunk || null;
    this.onStatusChange = callbacks.onStatusChange || null;

    // Check Speech Recognition capability
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      this.speechRecognition = new SpeechRecognition();
      this.speechRecognition.continuous = true;
      this.speechRecognition.interimResults = true;
      this.speechRecognition.lang = 'en-US';

      this.speechRecognition.onresult = (event) => {
        let interimText = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const transcriptSegment = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            if (this.onTranscriptChunk) {
              this.onTranscriptChunk({
                text: transcriptSegment.trim(),
                isFinal: true,
                timestamp: this.formatTime(this.elapsedSeconds),
                speaker: 'UNKNOWN' // User can re-assign or speaker switcher can alternate
              });
            }
          } else {
            interimText += transcriptSegment;
          }
        }
      };

      this.speechRecognition.onerror = (event) => {
        console.warn('Speech Recognition error:', event.error);
        if (event.error === 'not-allowed') {
          MediScribe.Toast.show('Microphone access denied. Please grant permission.', 'danger');
        }
      };
    }
  },

  async start() {
    // Check browser mediaDevices support
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      this.notifyUnsupported('Browser does not support navigator.mediaDevices.getUserMedia');
      return false;
    }

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });

      // Start MediaRecorder if available
      try {
        this.mediaRecorder = new MediaRecorder(this.stream);
        this.mediaRecorder.start(1000);
      } catch (mrError) {
        console.warn('MediaRecorder init failed, continuing with audio stream', mrError);
      }

      // Initialize Audio Visualizer
      this.setupVisualizer(this.stream);

      // Start Speech Recognition if supported
      if (this.speechRecognition) {
        try {
          this.speechRecognition.start();
        } catch (srErr) {
          console.warn('Speech recognition start note:', srErr);
        }
      } else {
        MediScribe.Toast.show('Live speech recognition is not supported in this browser. You can still record audio or use Demo Mode.', 'warning', 6000);
      }

      this.isRecording = true;
      this.isPaused = false;
      this.startTime = Date.now();
      this.elapsedSeconds = 0;
      this.startTimer();

      if (this.onStatusChange) {
        this.onStatusChange({
          state: 'recording',
          isRecording: true,
          isPaused: false,
          elapsed: '00:00'
        });
      }

      MediScribe.Audit.log('Microphone Started', 'Live microphone capture started via getUserMedia');
      return true;

    } catch (err) {
      console.error('Microphone error:', err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        MediScribe.Toast.show('Microphone permission denied by user or system.', 'danger');
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        MediScribe.Toast.show('No microphone device detected on this system.', 'warning');
      } else {
        MediScribe.Toast.show('Unable to access microphone: ' + err.message, 'danger');
      }
      return false;
    }
  },

  pause() {
    if (!this.isRecording || this.isPaused) return;
    this.isPaused = true;
    clearInterval(this.timerInterval);

    if (this.speechRecognition) {
      try { this.speechRecognition.stop(); } catch (e) {}
    }
    if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
      this.mediaRecorder.pause();
    }

    if (this.onStatusChange) {
      this.onStatusChange({
        state: 'paused',
        isRecording: true,
        isPaused: true,
        elapsed: this.formatTime(this.elapsedSeconds)
      });
    }
    MediScribe.Audit.log('Microphone Paused', 'Recording paused by user');
  },

  resume() {
    if (!this.isRecording || !this.isPaused) return;
    this.isPaused = false;
    this.startTimer();

    if (this.speechRecognition) {
      try { this.speechRecognition.start(); } catch (e) {}
    }
    if (this.mediaRecorder && this.mediaRecorder.state === 'paused') {
      this.mediaRecorder.resume();
    }

    if (this.onStatusChange) {
      this.onStatusChange({
        state: 'recording',
        isRecording: true,
        isPaused: false,
        elapsed: this.formatTime(this.elapsedSeconds)
      });
    }
    MediScribe.Audit.log('Microphone Resumed', 'Recording resumed by user');
  },

  stop() {
    if (!this.isRecording) return;
    this.isRecording = false;
    this.isPaused = false;
    clearInterval(this.timerInterval);

    if (this.speechRecognition) {
      try { this.speechRecognition.stop(); } catch (e) {}
    }
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      try { this.mediaRecorder.stop(); } catch (e) {}
    }
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
    }
    if (this.audioContext && this.audioContext.state !== 'closed') {
      try { this.audioContext.close(); } catch (e) {}
    }

    // Reset visualizer canvas
    const canvas = document.getElementById('audioVisualizer');
    if (canvas) {
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#0f172a';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    }

    const finalDuration = this.formatTime(this.elapsedSeconds);

    if (this.onStatusChange) {
      this.onStatusChange({
        state: 'stopped',
        isRecording: false,
        isPaused: false,
        elapsed: finalDuration
      });
    }

    MediScribe.Audit.log('Microphone Stopped', `Recording completed. Total duration: ${finalDuration}`);
    return finalDuration;
  },

  cancel() {
    this.stop();
    this.elapsedSeconds = 0;
    if (this.onStatusChange) {
      this.onStatusChange({
        state: 'cancelled',
        isRecording: false,
        isPaused: false,
        elapsed: '00:00'
      });
    }
    MediScribe.Toast.show('Recording cancelled and discarded.', 'info');
  },

  startTimer() {
    this.timerInterval = setInterval(() => {
      this.elapsedSeconds++;
      const formatted = this.formatTime(this.elapsedSeconds);
      const timerElem = document.getElementById('recordingTimerDisplay');
      if (timerElem) timerElem.textContent = formatted;
      if (this.onStatusChange) {
        this.onStatusChange({
          state: 'recording',
          isRecording: true,
          isPaused: false,
          elapsed: formatted
        });
      }
    }, 1000);
  },

  formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  },

  setupVisualizer(stream) {
    const canvas = document.getElementById('audioVisualizer');
    if (!canvas) return;
    const canvasCtx = canvas.getContext('2d');

    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;

    this.audioContext = new AudioContext();
    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 64;
    this.sourceNode = this.audioContext.createMediaStreamSource(stream);
    this.sourceNode.connect(this.analyser);

    const bufferLength = this.analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const draw = () => {
      if (!this.isRecording) return;
      this.animationFrameId = requestAnimationFrame(draw);

      this.analyser.getByteFrequencyData(dataArray);

      canvasCtx.fillStyle = '#0f172a';
      canvasCtx.fillRect(0, 0, canvas.width, canvas.height);

      const barWidth = (canvas.width / bufferLength) * 1.5;
      let x = 0;

      for (let i = 0; i < bufferLength; i++) {
        const barHeight = (dataArray[i] / 255) * (canvas.height - 6);
        // Medical cyan/teal gradient
        canvasCtx.fillStyle = this.isPaused ? '#64748b' : `rgb(2, ${132 + barHeight}, ${220})`;
        canvasCtx.fillRect(x, canvas.height - barHeight, barWidth - 2, barHeight);
        x += barWidth;
      }
    };

    draw();
  },

  notifyUnsupported(reason) {
    console.warn(reason);
    MediScribe.Toast.show('Microphone not supported in this environment. Falling back to synthetic demonstration.', 'warning');
    const warningNotice = document.getElementById('micUnsupportedNotice');
    if (warningNotice) warningNotice.style.display = 'block';
  }
};
