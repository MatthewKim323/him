'use client'

import { useEffect, useRef, useState } from 'react'
import styles from './page.module.css'

export default function Home() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [isLoaded, setIsLoaded] = useState(false)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const gl = canvas.getContext('webgl')
    if (!gl) {
      console.error('WebGL not supported')
      return
    }

    // Resize canvas
    const resize = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
      gl.viewport(0, 0, canvas.width, canvas.height)
    }
    resize()
    window.addEventListener('resize', resize)

    // Vertex shader (fullscreen quad)
    const vertexShaderSource = `
      attribute vec2 a_position;
      varying vec2 v_uv;
      
      void main() {
        v_uv = a_position * 0.5 + 0.5;
        gl_Position = vec4(a_position, 0.0, 1.0);
      }
    `

    // Fragment shader - The Universe Within by Martijn Steinrucken
    const fragmentShaderSource = `
      precision highp float;
      uniform float iTime;
      uniform vec2 iResolution;
      uniform vec2 iMouse;
      uniform sampler2D iChannel0;
      varying vec2 v_uv;
      
      #define S(a, b, t) smoothstep(a, b, t)
      #define NUM_LAYERS 4.0
      
      float N21(vec2 p) {
        vec3 a = fract(vec3(p.xyx) * vec3(213.897, 653.453, 253.098));
        a += dot(a, a.yzx + 79.76);
        return fract((a.x + a.y) * a.z);
      }
      
      vec2 GetPos(vec2 id, vec2 offs, float t) {
        float n = N21(id+offs);
        float n1 = fract(n*10.0);
        float n2 = fract(n*100.0);
        float a = t+n;
        return offs + vec2(sin(a*n1), cos(a*n2))*0.4;
      }
      
      float df_line( in vec2 a, in vec2 b, in vec2 p) {
        vec2 pa = p - a, ba = b - a;
        float h = clamp(dot(pa,ba) / dot(ba,ba), 0.0, 1.0);	
        return length(pa - ba * h);
      }
      
      float line(vec2 a, vec2 b, vec2 uv) {
        float r1 = 0.04;
        float r2 = 0.01;
        
        float d = df_line(a, b, uv);
        float d2 = length(a-b);
        float fade = S(1.5, 0.5, d2);
        
        fade += S(0.05, 0.02, abs(d2-0.75));
        return S(r1, r2, d)*fade;
      }
      
      float NetLayer(vec2 st, float n, float t) {
        vec2 id = floor(st)+n;
        
        st = fract(st)-0.5;
        
        vec2 p[9];
        p[0] = GetPos(id, vec2(-1.0, -1.0), t);
        p[1] = GetPos(id, vec2(0.0, -1.0), t);
        p[2] = GetPos(id, vec2(1.0, -1.0), t);
        p[3] = GetPos(id, vec2(-1.0, 0.0), t);
        p[4] = GetPos(id, vec2(0.0, 0.0), t);
        p[5] = GetPos(id, vec2(1.0, 0.0), t);
        p[6] = GetPos(id, vec2(-1.0, 1.0), t);
        p[7] = GetPos(id, vec2(0.0, 1.0), t);
        p[8] = GetPos(id, vec2(1.0, 1.0), t);
        
        float m = 0.0;
        float sparkle = 0.0;
        
        for(int i=0; i<9; i++) {
          m += line(p[4], p[i], st);
          
          float d = length(st-p[i]);
          
          float s = (0.005/(d*d));
          s *= S(1.0, 0.7, d);
          float pulse = sin((fract(p[i].x)+fract(p[i].y)+t)*5.0)*0.4+0.6;
          pulse = pow(pulse, 20.0);
          
          s *= pulse;
          sparkle += s;
        }
        
        m += line(p[1], p[3], st);
        m += line(p[1], p[5], st);
        m += line(p[7], p[5], st);
        m += line(p[7], p[3], st);
        
        float sPhase = (sin(t+n)+sin(t*0.1))*0.25+0.5;
        sPhase += pow(sin(t*0.1)*0.5+0.5, 50.0)*5.0;
        m += sparkle*sPhase;
        
        return m;
      }
      
      void main() {
        vec2 fragCoord = v_uv * iResolution;
        vec2 uv = (fragCoord-iResolution.xy*0.5)/iResolution.y;
        vec2 M = iMouse.xy/iResolution.xy-0.5;
        
        float t = iTime*0.1;
        
        float s = sin(t);
        float c = cos(t);
        mat2 rot = mat2(c, -s, s, c);
        vec2 st = uv*rot;  
        M *= rot*2.0;
        
        float m = 0.0;
        for(float i=0.0; i<1.0; i+=1.0/NUM_LAYERS) {
          float z = fract(t+i);
          float size = mix(15.0, 1.0, z);
          float fade = S(0.0, 0.6, z)*S(1.0, 0.8, z);
          
          m += fade * NetLayer(st*size-M*z, i, iTime);
        }
        
        float fft = texture2D(iChannel0, vec2(0.7, 0.0)).x;
        float glow = -uv.y*fft*2.0;
        
        vec3 baseCol = vec3(1.0);
        vec3 col = baseCol*m;
        col += baseCol*glow;
        
        col *= 1.0-dot(uv,uv);
        t = mod(iTime, 230.0);
        col *= S(0.0, 20.0, t)*S(224.0, 200.0, t);
        
        gl_FragColor = vec4(col,1.0);
      }
    `

    // Compile shader
    const compileShader = (source: string, type: number) => {
      const shader = gl.createShader(type)
      if (!shader) return null
      gl.shaderSource(shader, source)
      gl.compileShader(shader)
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
        console.error('Shader compile error:', gl.getShaderInfoLog(shader))
        gl.deleteShader(shader)
        return null
      }
      return shader
    }

    const vertexShader = compileShader(vertexShaderSource, gl.VERTEX_SHADER)
    const fragmentShader = compileShader(fragmentShaderSource, gl.FRAGMENT_SHADER)
    
    if (!vertexShader || !fragmentShader) return

    // Create program
    const program = gl.createProgram()
    if (!program) return
    
    gl.attachShader(program, vertexShader)
    gl.attachShader(program, fragmentShader)
    gl.linkProgram(program)
    
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.error('Program link error:', gl.getProgramInfoLog(program))
      return
    }

    // Setup geometry (fullscreen quad)
    const positionBuffer = gl.createBuffer()
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer)
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
      -1, -1,
       1, -1,
      -1,  1,
      -1,  1,
       1, -1,
       1,  1,
    ]), gl.STATIC_DRAW)

    const positionLocation = gl.getAttribLocation(program, 'a_position')
    const timeLocation = gl.getUniformLocation(program, 'iTime')
    const resolutionLocation = gl.getUniformLocation(program, 'iResolution')
    const mouseLocation = gl.getUniformLocation(program, 'iMouse')
    const channel0Location = gl.getUniformLocation(program, 'iChannel0')

    // Create a simple texture for iChannel0 (FFT - we'll use a default value)
    const fftTexture = gl.createTexture()
    gl.bindTexture(gl.TEXTURE_2D, fftTexture)
    const fftData = new Uint8Array([128, 128, 128, 255]) // Default gray value
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, fftData)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR)

    // Mouse tracking
    let mouseX = 0
    let mouseY = 0
    const handleMouseMove = (e: MouseEvent) => {
      mouseX = e.clientX
      mouseY = e.clientY
    }
    window.addEventListener('mousemove', handleMouseMove)

    // Animation loop
    let animationId: number
    const startTime = Date.now()

    const render = () => {
      const time = (Date.now() - startTime) / 1000.0

      gl.useProgram(program)
      gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer)
      gl.enableVertexAttribArray(positionLocation)
      gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0)

      gl.uniform1f(timeLocation, time)
      gl.uniform2f(resolutionLocation, canvas.width, canvas.height)
      gl.uniform2f(mouseLocation, mouseX, mouseY)
      
      gl.activeTexture(gl.TEXTURE0)
      gl.bindTexture(gl.TEXTURE_2D, fftTexture)
      gl.uniform1i(channel0Location, 0)

      gl.drawArrays(gl.TRIANGLES, 0, 6)

      animationId = requestAnimationFrame(render)
    }

    render()

    // Trigger load animation after a brief moment
    const timer = setTimeout(() => {
      setIsLoaded(true)
    }, 50)

    return () => {
      window.removeEventListener('resize', resize)
      window.removeEventListener('mousemove', handleMouseMove)
      cancelAnimationFrame(animationId)
      clearTimeout(timer)
    }
  }, [])

  return (
    <main className={styles.main}>
      <canvas 
        ref={canvasRef} 
        className={`${styles.canvas} ${isLoaded ? styles.canvasLoaded : ''}`} 
      />
      <div className={`${styles.dimOverlay} ${isLoaded ? styles.dimOverlayLoaded : ''}`} />
      <div className={styles.titleContainer}>
        <div className={styles.title}>
          <span className={`${styles.titleChar} ${isLoaded ? styles.titleCharLoaded : ''}`} style={{ animationDelay: '0.6s' }}>H</span>
          <span className={`${styles.titleChar} ${isLoaded ? styles.titleCharLoaded : ''}`} style={{ animationDelay: '0.7s' }}>I</span>
          <span className={`${styles.titleChar} ${isLoaded ? styles.titleCharLoaded : ''}`} style={{ animationDelay: '0.8s' }}>M</span>
        </div>
        <div className={`${styles.subtitle} ${isLoaded ? styles.subtitleLoaded : ''}`}>
          measure your training
        </div>
      </div>
    </main>
  )
}
