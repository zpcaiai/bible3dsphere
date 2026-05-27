import { Component, useMemo, useRef, useEffect, useCallback, useState } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { Bloom, EffectComposer } from '@react-three/postprocessing'
import { Billboard, Html, OrbitControls, Stars, Text } from '@react-three/drei'
import * as THREE from 'three'
import { useEmotionStore } from './store'
import TranslatableParagraph from './TranslatableParagraph'

const SPHERE_RADIUS = 4.18
// Generate a visually distinct color for each of the 171 points
function pointColor(index, total) {
  const hue = (index / total) * 360
  const sat = 70 + (index % 5) * 4
  const lit = 62 + (index % 3) * 5
  return `hsl(${hue.toFixed(1)},${sat}%,${lit}%)`
}

// ─── Error Boundary ──────────────────────────────────────────────────────────
class SceneErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null, retries: 0 }
    this.handleRetry = this.handleRetry.bind(this)
  }
  static getDerivedStateFromError(error) { return { error } }
  componentDidCatch(error, info) {
    console.error('[EmotionSphere] 3D scene crashed:', error, info)
  }
  handleRetry() {
    this.setState(s => ({ error: null, retries: s.retries + 1 }))
  }
  render() {
    if (this.state.error) {
      const { layoutItems = [], onSelectFeature } = this.props
      return (
        <div style={{
          padding: '20px 16px',
          background: 'rgba(30,20,60,0.95)',
          borderRadius: '16px',
          border: '1px solid rgba(255,100,100,0.25)',
          minHeight: 240,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
            <span style={{ fontSize: 13, color: 'rgba(255,150,150,0.8)', fontWeight: 600 }}>
              ⚠️ 3D 星球暂时无法渲染
            </span>
            <button
              onClick={this.handleRetry}
              style={{
                fontSize: 11, padding: '4px 12px',
                background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.2)',
                borderRadius: 20, color: 'rgba(255,255,255,0.7)', cursor: 'pointer',
              }}
            >
              重试 3D
            </button>
          </div>
          {/* 2D 情感节点列表降级视图 */}
          <div style={{ fontSize: 12, color: 'rgba(180,180,255,0.6)', marginBottom: 10 }}>以下是情感节点列表（2D 降级模式）：</div>
          <div style={{
            display: 'flex', flexWrap: 'wrap', gap: '6px',
            maxHeight: 200, overflowY: 'auto',
          }}>
            {(layoutItems || []).slice(0, 40).map((item, i) => (
              <button
                key={item.feature_key || i}
                onClick={() => onSelectFeature && onSelectFeature(item.feature_key)}
                style={{
                  fontSize: 11, padding: '3px 9px',
                  background: 'rgba(88,86,214,0.2)', border: '1px solid rgba(88,86,214,0.35)',
                  borderRadius: 14, color: '#a5b4fc', cursor: 'pointer',
                  whiteSpace: 'nowrap',
                }}
              >
                {item.label || item.description?.slice(0, 18) || item.feature_key}
              </button>
            ))}
          </div>
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
    const lod = d > 7.5 ? 'far' : d > 5 ? 'mid' : 'near'
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
      <sphereGeometry args={[SPHERE_RADIUS - 0.055, 48, 48]} />
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
      <sphereGeometry args={[0.099, 12, 12]} />
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
function AllPointLabels({ items, hoveredKey, selectedKey, onHover, onSelect }) {
  const zoomLevel = useEmotionStore((s) => s.zoomLevel)
  const total = items.length || 1

  return items.map((item, i) => {
    const pos = safeNormalizedPos(item.x, item.y, item.z, SPHERE_RADIUS * 1.243)
    if (!pos) return null
    const isActive = item.feature_key === selectedKey
    const isHov = item.feature_key === hoveredKey
    const baseColor = pointColor(i, total)
    const color = isActive ? '#ffe066' : isHov ? '#ffffff' : baseColor
    const fontSize = isActive ? 0.242 : isHov ? 0.209
      : zoomLevel === 'far' ? 0.143
      : zoomLevel === 'mid' ? 0.154
      : 0.165
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
          onPointerOver={(e) => { e.stopPropagation(); onHover?.(item) }}
          onPointerOut={(e) => { e.stopPropagation(); onHover?.(null) }}
          onClick={(e) => { e.stopPropagation(); onSelect?.(item) }}
          cursor="pointer"
        >
          {itemLabel(item)}
        </Text>
      </Billboard>
    )
  })
}

// ─── 3D Verse Popover ────────────────────────────────────────────────────────
function VersePopover3D({ 
  feature, 
  detail, 
  zoomScale = 1.0, 
  onClose,
  expandedVerseId,
  versePrayers,
  versePrayerLoading,
  handleVerseClick
}) {
  const sphereGuidance = useEmotionStore((s) => s.sphereGuidance)
  const sphereBiblicalExample = useEmotionStore((s) => s.sphereBiblicalExample)
  if (!feature) return null
  const pos = safeNormalizedPos(feature.x, feature.y, feature.z, SPHERE_RADIUS * 1.322)
  if (!pos) return null
  const verses = (detail?.matches?.cuv || []).slice(0, 4)
  const isLoading = !sphereGuidance && !sphereBiblicalExample
  // Dynamic distance factor and CSS size based on zoom scale
  const distanceFactor = 6 / zoomScale
  const cssWidth = 320 * zoomScale
  const cssMaxHeight = 520 * zoomScale
  return (
    <Html position={pos.toArray()} distanceFactor={distanceFactor} center zIndexRange={[100, 0]}>
      <div 
        className="verse-popover-3d glass-float" 
        style={{ width: `${cssWidth}px`, maxHeight: `${cssMaxHeight}px` }}
      >
        <button className="vp-close" onClick={onClose}>✕</button>
        <div className="vp-scroll-body" style={{ maxHeight: `${cssMaxHeight}px` }}>
        <div className="vp-header">
          <span className="vp-key">
            {feature.zh_label
              ? <>{feature.zh_label} <small style={{opacity:0.5, fontWeight:400}}>#{feature.feature_id}</small></>
              : `${feature.layer}:${feature.feature_id}`}
          </span>
        </div>
        {isLoading && (
          <div className="vp-loading">沈思中…</div>
        )}

        {sphereGuidance && (
          <div className="vp-section">
            <div className="vp-section-title">灵魂处境</div>
            {sphereGuidance.core_emotions?.length > 0 && (
              <div className="vp-emotion-tags">
                {sphereGuidance.core_emotions.map((e) => (
                  <span key={e} className="vp-emotion-tag">{e}</span>
                ))}
              </div>
            )}
            {sphereGuidance.psychological_assessment && (
              <TranslatableParagraph className="vp-body">{sphereGuidance.psychological_assessment}</TranslatableParagraph>
            )}
            {sphereGuidance.core_need && (
              <div className="vp-core-need">{sphereGuidance.core_need}</div>
            )}
            {sphereGuidance.coping_suggestions?.length > 0 && (
              <ul className="vp-tips">
                {sphereGuidance.coping_suggestions.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            )}
            {sphereGuidance.spiritual_guidance && (
              <TranslatableParagraph className="vp-spiritual">{sphereGuidance.spiritual_guidance}</TranslatableParagraph>
            )}
          </div>
        )}

        {sphereBiblicalExample && (
          <div className="vp-section">
            <div className="vp-divider" />
            <div className="vp-section-title">圣经榜样</div>
            <div className="vp-person-row">
              <strong>{sphereBiblicalExample.person}</strong>
              {sphereBiblicalExample.era && <span className="vp-era">{sphereBiblicalExample.era}</span>}
            </div>
            {sphereBiblicalExample.similar_situation && <TranslatableParagraph className="vp-body">{sphereBiblicalExample.similar_situation}</TranslatableParagraph>}
            {sphereBiblicalExample.biblical_response && <TranslatableParagraph className="vp-body">{sphereBiblicalExample.biblical_response}</TranslatableParagraph>}
            {sphereBiblicalExample.key_verse && (
              <TranslatableParagraph className="vp-spiritual" style={{fontStyle:'italic'}}>{sphereBiblicalExample.key_verse}</TranslatableParagraph>
            )}
            {sphereBiblicalExample.application && (
              <TranslatableParagraph className="vp-core-need">{sphereBiblicalExample.application}</TranslatableParagraph>
            )}
          </div>
        )}

        {verses.length > 0 && (
          <div className="vp-section">
            <div className="vp-divider" />
            <div className="vp-section-title vp-section-title-meditation">默想经文</div>
            <div className="vp-verses">
              {verses.map((v, vi) => (
                <div key={v.pk_id ?? vi} className="vp-verse-wrapper">
                  <div 
                    className={`vp-verse ${expandedVerseId === v.pk_id ? 'vp-verse-active' : ''}`}
                    onClick={() => handleVerseClick?.(v)}
                  >
                    <div className="vp-verse-ref-row">
                      <span className="vp-ref">{v.book_name} {v.chapter}:{v.verse}</span>
                      <span className={`vp-chevron ${expandedVerseId === v.pk_id ? 'open' : ''}`}>▼</span>
                    </div>
                    <TranslatableParagraph className="vp-text">{v.raw_text}</TranslatableParagraph>
                  </div>
                  {expandedVerseId === v.pk_id && (
                    <div className="vp-prayer-block">
                      <div className="vp-prayer-label">🙏 经文祷告</div>
                      {versePrayerLoading === v.pk_id ? (
                        <div className="vp-prayer-loading">✨ 正在生成祷告...</div>
                      ) : versePrayers?.[v.pk_id] ? (
                        <TranslatableParagraph className="vp-prayer-text">{versePrayers[v.pk_id]}</TranslatableParagraph>
                      ) : null}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
        </div>
      </div>
    </Html>
  )
}


// ─── Community Halo Rings ────────────────────────────────────────────────────
// Renders semi-transparent torus rings around the sphere, one per top community
// emotion.  Ring radius grows outward; opacity & tube thickness scale with %.
function CommunityHaloRings ({ emotions }) {
  const groupRef = useRef()

  // Slowly counter-rotate the whole halo group for a living feel
  useFrame((_, dt) => {
    if (groupRef.current) groupRef.current.rotation.y -= dt * 0.018
  })

  if (!emotions || emotions.length === 0) return null

  // Layout: top-6 rings starting at radius 5.2, stepping out by 0.55
  const BASE_RADIUS = 5.2
  const STEP        = 0.55
  const MAX_RINGS   = 6

  return (
    <group ref={groupRef}>
      {emotions.slice(0, MAX_RINGS).map((em, i) => {
        const ringRadius = BASE_RADIUS + i * STEP
        // Tube thickness: 0.04 (weak emotion) → 0.18 (dominant emotion)
        const tube = 0.04 + (em.pct / 100) * 0.18
        // Opacity: 0.10 → 0.45
        const opacity = 0.10 + (em.pct / 100) * 0.40

        // Parse hex colour
        const colour = em.colour || '#aaaaaa'

        // Each ring tilts slightly differently so they don't overlap perfectly
        const tiltX = (i * 0.32) % (Math.PI * 2)
        const tiltZ = (i * 0.19) % (Math.PI * 2)

        return (
          <mesh
            key={em.label || i}
            rotation={[tiltX, 0, tiltZ]}
          >
            <torusGeometry args={[ringRadius, tube, 16, 80]} />
            <meshStandardMaterial
              color={colour}
              transparent
              opacity={opacity}
              emissive={colour}
              emissiveIntensity={0.45}
              depthWrite={false}
              side={2}  /* THREE.DoubleSide */
            />
          </mesh>
        )
      })}
    </group>
  )
}

// ─── Main Sphere ─────────────────────────────────────────────────────────────
function EmotionSphere({ 
  onVerseTrigger,
  expandedVerseId,
  versePrayers,
  versePrayerLoading,
  handleVerseClick
}) {
  const layoutItems = useEmotionStore((s) => s.layoutItems)
  const communityHeatmap = useEmotionStore((s) => s.communityHeatmap)
  const selectedFeature = useEmotionStore((s) => s.selectedFeature)
  const selectedFeatureDetail = useEmotionStore((s) => s.selectedFeatureDetail)
  const setSelectedFeature = useEmotionStore((s) => s.setSelectedFeature)
  const hovered = useEmotionStore((s) => s.hovered)
  const setHovered = useEmotionStore((s) => s.setHovered)
  const zoomLevel = useEmotionStore((s) => s.zoomLevel)
  const groupRef = useRef()

  useFrame((_, dt) => {
    if (groupRef.current) groupRef.current.rotation.y += dt * 0.033
  })

  const handleHover = useCallback((item) => {
    setHovered(item ? item.feature_key : null)
  }, [setHovered])

  const handleSelect = useCallback((item) => {
    setSelectedFeature(item)
    onVerseTrigger?.(item)
  }, [setSelectedFeature, onVerseTrigger])

  // Calculate popover scale based on zoom level
  const popoverScale = zoomLevel === 'far' ? 0.88 : zoomLevel === 'mid' ? 1.1 : 1.43

  return (
    <group ref={groupRef} position={[0, 0, 0]} onPointerMissed={() => { setSelectedFeature(null); setHovered(null) }}>
      <SphereShell />
      <CommunityHaloRings emotions={communityHeatmap} />
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
        onHover={handleHover}
        onSelect={handleSelect}
      />
      <VersePopover3D
        feature={selectedFeature}
        detail={selectedFeatureDetail}
        zoomScale={popoverScale}
        onClose={() => setSelectedFeature(null)}
        expandedVerseId={expandedVerseId}
        versePrayers={versePrayers}
        versePrayerLoading={versePrayerLoading}
        handleVerseClick={handleVerseClick}
      />
    </group>
  )
}

// ─── Scene Root ──────────────────────────────────────────────────────────────
export function EmotionSphereScene({ 
  onVerseTrigger,
  expandedVerseId,
  versePrayers,
  versePrayerLoading,
  handleVerseClick,
  onSelectFeature,
}) {
  const layoutItems = useEmotionStore((s) => s.layoutItems)
  return (
    <SceneErrorBoundary layoutItems={layoutItems} onSelectFeature={onSelectFeature}>
      <Canvas style={{ width: '100%', height: '100%', display: 'block' }} camera={{ position: [0, 0, 8.8], fov: 48 }} dpr={[1, 2]}>
        <color attach="background" args={['#060b18']} />
        <fog attach="fog" args={['#060b18', 8.5, 19]} />
        <ambientLight intensity={0.8} />
        <directionalLight position={[5, 7, 4]} intensity={1.3} />
        <pointLight position={[-6, -5, -3]} intensity={1.1} color="#5577ff" />
        <Stars radius={38} depth={30} count={2500} factor={3.1} saturation={0} fade speed={0.3} />

        <EmotionSphere 
          onVerseTrigger={onVerseTrigger}
          expandedVerseId={expandedVerseId}
          versePrayers={versePrayers}
          versePrayerLoading={versePrayerLoading}
          handleVerseClick={handleVerseClick}
        />

        <OrbitControls enablePan={false} minDistance={2.8} maxDistance={18} />
        <CameraLODWatcher />
        <EffectComposer>
          <Bloom mipmapBlur intensity={0.9} luminanceThreshold={0.18} luminanceSmoothing={0.5} />
        </EffectComposer>
      </Canvas>
    </SceneErrorBoundary>
  )
}
