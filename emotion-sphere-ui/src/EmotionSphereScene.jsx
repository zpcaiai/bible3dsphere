import { Component, useMemo, useRef, useEffect, useCallback } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { Bloom, EffectComposer } from '@react-three/postprocessing'
import { Billboard, Html, OrbitControls, Stars, Text } from '@react-three/drei'
import * as THREE from 'three'
import { useEmotionStore } from './store'

const SPHERE_RADIUS = 5
// Generate a visually distinct color for each of the 171 points
function pointColor(index, total) {
  const hue = (index / total) * 360
  const sat = 70 + (index % 5) * 4
  const lit = 62 + (index % 3) * 5
  return `hsl(${hue.toFixed(1)},${sat}%,${lit}%)`
}

// ─── Error Boundary ──────────────────────────────────────────────────────────
class SceneErrorBoundary extends Component {
  constructor(props) { super(props); this.state = { error: null } }
  static getDerivedStateFromError(error) { return { error } }
  render() {
    if (this.state.error) {
      return (
        <div style={{ color: '#ff8080', padding: 24, fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
          <b>3D Scene Error:</b>{'\n'}{String(this.state.error)}
        </div>
      )
    }
    return this.props.children
  }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
function safeNormalizedPos(x, y, z, scale = SPHERE_RADIUS) {
  const v = new THREE.Vector3(x ?? 0, y ?? 0, z ?? 0)
  const len = v.length()
  if (len < 1e-6) return null
  return v.normalize().multiplyScalar(scale)
}

// ─── LOD Camera Watcher ──────────────────────────────────────────────────────
function CameraLODWatcher() {
  const camera = useThree((s) => s.camera)
  const setZoomLevel = useEmotionStore((s) => s.setZoomLevel)
  const prev = useRef('')
  useFrame(() => {
    const d = camera.position.length()
    const lod = d > 9 ? 'far' : d > 5.5 ? 'mid' : 'near'
    if (lod !== prev.current) { prev.current = lod; setZoomLevel(lod) }
  })
  return null
}

// ─── Wireframe shell ─────────────────────────────────────────────────────────
function SphereShell() {
  const ref = useRef()
  useFrame((_, dt) => { if (ref.current) ref.current.rotation.y += dt * 0.045 })
  return (
    <mesh ref={ref}>
      <sphereGeometry args={[SPHERE_RADIUS - 0.05, 48, 48]} />
      <meshPhysicalMaterial color="#3a5fff" transparent opacity={0.055}
        roughness={0.1} metalness={0.3} clearcoat={1} wireframe />
    </mesh>
  )
}

// ─── Instanced Points ────────────────────────────────────────────────────────
function InstancedPoints({ items, onHover, onSelect, selectedKey, hoveredKey }) {
  const meshRef = useRef()
  const dummy = useMemo(() => new THREE.Object3D(), [])
  const count = items.length

  // Initialise matrices + colors once mesh mounts
  useEffect(() => {
    const mesh = meshRef.current
    if (!mesh || !count) return
    const col = new THREE.Color()
    items.forEach((item, i) => {
      const pos = safeNormalizedPos(item.x, item.y, item.z)
      if (!pos) return
      dummy.position.copy(pos)
      dummy.scale.setScalar(1)
      dummy.updateMatrix()
      mesh.setMatrixAt(i, dummy.matrix)
      col.set(pointColor(i, count))
      mesh.setColorAt(i, col)
    })
    mesh.instanceMatrix.needsUpdate = true
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true
  }, [items, count, dummy])

  // Sync all instances every frame so hover/active changes are always reflected
  const prevSelectedRef = useRef(null)
  const prevHoveredRef = useRef(null)
  useFrame(() => {
    const mesh = meshRef.current
    if (!mesh || !count) return
    if (prevSelectedRef.current === selectedKey && prevHoveredRef.current === hoveredKey) return
    prevSelectedRef.current = selectedKey
    prevHoveredRef.current = hoveredKey
    const col = new THREE.Color()
    items.forEach((item, i) => {
      const isActive = item.feature_key === selectedKey
      const isHov = item.feature_key === hoveredKey
      const pos = safeNormalizedPos(item.x, item.y, item.z)
      if (!pos) return
      dummy.position.copy(pos)
      dummy.scale.setScalar(isActive ? 1.9 : isHov ? 1.45 : 1.0)
      dummy.updateMatrix()
      mesh.setMatrixAt(i, dummy.matrix)
      col.set(isActive ? '#ffe066' : isHov ? '#ffffff' : pointColor(i, count))
      mesh.setColorAt(i, col)
    })
    mesh.instanceMatrix.needsUpdate = true
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true
  })

  const handlePointerMove = useCallback((e) => {
    e.stopPropagation()
    if (e.instanceId != null && items[e.instanceId]) onHover(items[e.instanceId])
  }, [items, onHover])

  const handlePointerOut = useCallback((e) => {
    e.stopPropagation()
    onHover(null)
  }, [onHover])

  const handleClick = useCallback((e) => {
    e.stopPropagation()
    if (e.instanceId != null && items[e.instanceId]) onSelect(items[e.instanceId])
  }, [items, onSelect])

  if (!count) return null
  return (
    <instancedMesh
      ref={meshRef}
      args={[null, null, count]}
      onPointerMove={handlePointerMove}
      onPointerOut={handlePointerOut}
      onClick={handleClick}
    >
      <sphereGeometry args={[0.09, 12, 12]} />
      <meshStandardMaterial vertexColors emissive="#1533ff" emissiveIntensity={0.4} />
    </instancedMesh>
  )
}

function itemLabel(item) {
  const zh = item.zh_label || ''
  const en = item.short_en || item.source_keyword || ''
  if (zh && en) return `${zh}(${en})`
  return zh || en || ''
}

// ─── All Point Labels — 3D Text, always visible, uniform sphere coverage ──────
function AllPointLabels({ items, hoveredKey, selectedKey }) {
  const zoomLevel = useEmotionStore((s) => s.zoomLevel)
  const total = items.length || 1

  return items.map((item, i) => {
    const pos = safeNormalizedPos(item.x, item.y, item.z, SPHERE_RADIUS * 1.13)
    if (!pos) return null
    const isActive = item.feature_key === selectedKey
    const isHov = item.feature_key === hoveredKey
    const baseColor = pointColor(i, total)
    const color = isActive ? '#ffe066' : isHov ? '#ffffff' : baseColor
    const fontSize = isActive ? 0.22 : isHov ? 0.19
      : zoomLevel === 'far' ? 0.13
      : zoomLevel === 'mid' ? 0.14
      : 0.15
    return (
      <Billboard key={item.feature_key} position={pos.toArray()} follow={true}>
        <Text
          fontSize={fontSize}
          color={color}
          anchorX="center"
          anchorY="middle"
          outlineColor="#020610"
          outlineWidth={isActive || isHov ? 0.018 : 0.008}
          fillOpacity={isActive || isHov ? 1 : 0.92}
          depthOffset={isActive || isHov ? -2 : 0}
        >
          {itemLabel(item)}
        </Text>
      </Billboard>
    )
  })
}

// ─── 3D Verse Popover ────────────────────────────────────────────────────────
function VersePopover3D({ feature, detail, onClose }) {
  if (!feature) return null
  const pos = safeNormalizedPos(feature.x, feature.y, feature.z, SPHERE_RADIUS * 1.22)
  if (!pos) return null
  const verses = [
    ...(detail?.matches?.cuv || []).slice(0, 2),
    ...(detail?.matches?.esv || []).slice(0, 2),
  ]
  return (
    <Html position={pos.toArray()} distanceFactor={6} center zIndexRange={[100, 0]}>
      <div className="verse-popover-3d glass-float">
        <div className="vp-header">
          <span className="vp-key">
            {feature.zh_label
              ? <>{feature.zh_label} <small style={{opacity:0.5, fontWeight:400}}>#{feature.feature_id}</small></>
              : `${feature.layer}:${feature.feature_id}`}
          </span>
          <button className="vp-close" onClick={onClose}>✕</button>
        </div>
        <div className="vp-explanation">{feature.explanation}</div>
        {verses.length > 0 && (
          <div className="vp-verses">
            {verses.map((v, vi) => (
              <div key={v.pk_id ?? vi} className="vp-verse">
                <span className="vp-ref">{v.book_name} {v.chapter}:{v.verse}</span>
                <p className="vp-text">{v.raw_text}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </Html>
  )
}

// ─── Main Sphere ─────────────────────────────────────────────────────────────
function EmotionSphere({ onVerseTrigger }) {
  const layoutItems = useEmotionStore((s) => s.layoutItems)
  const selectedFeature = useEmotionStore((s) => s.selectedFeature)
  const selectedFeatureDetail = useEmotionStore((s) => s.selectedFeatureDetail)
  const setSelectedFeature = useEmotionStore((s) => s.setSelectedFeature)
  const hovered = useEmotionStore((s) => s.hovered)
  const setHovered = useEmotionStore((s) => s.setHovered)
  const groupRef = useRef()

  useFrame((_, dt) => {
    if (groupRef.current) groupRef.current.rotation.y += dt * 0.03
  })

  const handleHover = useCallback((item) => {
    setHovered(item ? item.feature_key : null)
  }, [setHovered])

  const handleSelect = useCallback((item) => {
    setSelectedFeature(item)
    onVerseTrigger?.(item)
  }, [setSelectedFeature, onVerseTrigger])

  return (
    <group ref={groupRef} onPointerMissed={() => { setSelectedFeature(null); setHovered(null) }}>
      <SphereShell />
      <InstancedPoints
        items={layoutItems}
        onHover={handleHover}
        onSelect={handleSelect}
        selectedKey={selectedFeature?.feature_key}
        hoveredKey={hovered}
      />
      <AllPointLabels
        items={layoutItems}
        hoveredKey={hovered}
        selectedKey={selectedFeature?.feature_key}
      />
      <VersePopover3D
        feature={selectedFeature}
        detail={selectedFeatureDetail}
        onClose={() => setSelectedFeature(null)}
      />
    </group>
  )
}

// ─── Scene Root ──────────────────────────────────────────────────────────────
export function EmotionSphereScene({ onVerseTrigger }) {
  return (
    <SceneErrorBoundary>
      <Canvas camera={{ position: [0, 0, 13], fov: 45 }} dpr={[1, 2]}>
        <color attach="background" args={['#060b18']} />
        <fog attach="fog" args={['#060b18', 12, 26]} />
        <ambientLight intensity={0.8} />
        <directionalLight position={[5, 7, 4]} intensity={1.3} />
        <pointLight position={[-6, -5, -3]} intensity={1.1} color="#5577ff" />
        <Stars radius={45} depth={35} count={2800} factor={3.2} saturation={0} fade speed={0.3} />

        <EmotionSphere onVerseTrigger={onVerseTrigger} />

        <OrbitControls enablePan={false} minDistance={3} maxDistance={22} />
        <CameraLODWatcher />
        <EffectComposer>
          <Bloom mipmapBlur intensity={0.9} luminanceThreshold={0.18} luminanceSmoothing={0.5} />
        </EffectComposer>
      </Canvas>
    </SceneErrorBoundary>
  )
}
