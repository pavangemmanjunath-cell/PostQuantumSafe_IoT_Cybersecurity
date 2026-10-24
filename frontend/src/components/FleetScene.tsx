import { Line, OrbitControls } from "@react-three/drei";
import { Canvas, useFrame } from "@react-three/fiber";
import type { icons } from "lucide";
import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import type { SimDevice } from "../api/types";
import { DEVICE_ICON, iconImage, PERSONA_ICON } from "./icons";

const STATUS_COLOR = { ok: "#22c55e", warning: "#f59e0b", alert: "#ef4444" } as const;
const ADVERSARY: [number, number, number] = [11.5, 0, -9];
const ANALYST: [number, number, number] = [-7, 0, 8];
const QUANTUM_ATTACKS = new Set(["hndl_capture", "tls_downgrade", "pq_strip", "cert_spoof"]);
const NETWORK_ATTACKS = new Set(["syn_flood", "ddos_volumetric", "port_scan", "mqtt_malformed", "arp_spoofing"]);
const SHORT: Record<string, string> = {
  hndl_capture: "HNDL capture", tls_downgrade: "TLS downgrade", pq_strip: "PQ fallback", cert_spoof: "Cert forgery",
  syn_flood: "SYN flood", ddos_volumetric: "DDoS", port_scan: "Port scan", mqtt_malformed: "Bad MQTT", arp_spoofing: "MITM",
  prompt_injection: "Prompt injection", pq_downgrade_prompt: "PQ-downgrade prompt", phi_leak: "PHI leak",
  unsafe_command: "Unsafe command", secret_leak: "Secret leak",
};

/** Round icon badge rendered to a canvas texture (Lucide vector → WebGL sprite). */
function useBadgeTexture(icon: keyof typeof icons, ring: string, fill = "#0b1426") {
  const tex = useMemo(() => {
    const c = document.createElement("canvas");
    c.width = c.height = 256;
    const t = new THREE.CanvasTexture(c);
    t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = 4;
    return t;
  }, []);
  useEffect(() => {
    let alive = true;
    const c = tex.image as HTMLCanvasElement;
    const ctx = c.getContext("2d")!;
    const draw = (img?: HTMLImageElement) => {
      ctx.clearRect(0, 0, 256, 256);
      ctx.beginPath();
      ctx.arc(128, 128, 112, 0, Math.PI * 2);
      ctx.fillStyle = fill;
      ctx.fill();
      ctx.lineWidth = 14;
      ctx.strokeStyle = ring;
      ctx.stroke();
      if (img) ctx.drawImage(img, 64, 64, 128, 128);
      tex.needsUpdate = true;
    };
    draw();
    iconImage(icon, "#e2e8f0", 128).then((img) => alive && draw(img)).catch(() => undefined);
    return () => { alive = false; };
  }, [tex, icon, ring, fill]);
  useEffect(() => () => tex.dispose(), [tex]);
  return tex;
}

function Label({ text, position, tone = "default", size = 0.5 }: {
  text: string; position: [number, number, number]; tone?: "default" | "alert" | "selected" | "analyst"; size?: number;
}) {
  const texture = useMemo(() => {
    const s = 2;
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d")!;
    const font = `600 ${22 * s}px Inter, system-ui, sans-serif`;
    ctx.font = font;
    const w = Math.ceil(ctx.measureText(text).width) + 28 * s;
    const h = 40 * s;
    canvas.width = w;
    canvas.height = h;
    ctx.font = font;
    ctx.fillStyle = tone === "alert" ? "rgba(69, 10, 10, 0.92)" : "rgba(6, 12, 26, 0.88)";
    ctx.strokeStyle = { alert: "#ef4444", selected: "#38bdf8", analyst: "#22d3ee", default: "#2b3a5c" }[tone];
    ctx.lineWidth = 3 * s;
    ctx.beginPath();
    ctx.roundRect(2, 2, w - 4, h - 4, 10 * s);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = tone === "alert" ? "#fecaca" : "#e2e8f0";
    ctx.textBaseline = "middle";
    ctx.fillText(text, 14 * s, h / 2 + 1);
    const tex = new THREE.CanvasTexture(canvas);
    tex.colorSpace = THREE.SRGBColorSpace;
    return { tex, aspect: w / h };
  }, [text, tone]);
  useEffect(() => () => texture.tex.dispose(), [texture]);
  return (
    <sprite position={position} scale={[size * texture.aspect, size, 1]} renderOrder={10}>
      <spriteMaterial map={texture.tex} transparent depthTest={false} />
    </sprite>
  );
}

function Badge({ icon, ring, position, scale = 1.25, fill }: {
  icon: keyof typeof icons; ring: string; position: [number, number, number]; scale?: number; fill?: string;
}) {
  const tex = useBadgeTexture(icon, ring, fill);
  return (
    <sprite position={position} scale={[scale, scale, 1]} renderOrder={5}>
      <spriteMaterial map={tex} transparent depthWrite={false} />
    </sprite>
  );
}

function DeviceNode({ d, selected, assessing, onSelect }: { d: SimDevice; selected: boolean; assessing: boolean; onSelect: (id: string) => void }) {
  const ring = useRef<THREE.Mesh>(null);
  const glow = useRef<THREE.Mesh>(null);
  const color = STATUS_COLOR[d.live.status];
  const [x, z] = d.position;
  const hub = d.shape === "hub";
  const issues = d.active_attacks.map((a) => SHORT[a] ?? a);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    if (ring.current) {
      const p = (t * 0.8) % 1;
      ring.current.scale.setScalar(1 + p * 1.6);
      (ring.current.material as THREE.MeshBasicMaterial).opacity = 0.65 * (1 - p);
    }
    if (glow.current) (glow.current.material as THREE.MeshBasicMaterial).opacity = assessing ? 0.35 + 0.25 * Math.sin(t * 6) : 0.18;
  });

  return (
    <group position={[x, 0, z]}>
      <mesh position={[0, 0.12, 0]} onClick={(e) => { e.stopPropagation(); onSelect(d.id); }}
        onPointerOver={() => (document.body.style.cursor = "pointer")} onPointerOut={() => (document.body.style.cursor = "")}>
        <cylinderGeometry args={[hub ? 1.2 : 0.85, hub ? 1.35 : 0.95, 0.24, 48]} />
        <meshStandardMaterial color="#111c33" emissive={color} emissiveIntensity={0.35} metalness={0.5} roughness={0.35} />
      </mesh>
      <mesh ref={glow} position={[0, 1.1, 0]}>
        <cylinderGeometry args={[0.05, 0.05, 1.8, 8]} />
        <meshBasicMaterial color={assessing ? "#22d3ee" : color} transparent opacity={0.2} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]}>
        <ringGeometry args={[1.05, selected ? 1.3 : 1.12, 64]} />
        <meshBasicMaterial color={selected ? "#38bdf8" : color} transparent opacity={selected ? 0.95 : 0.45} />
      </mesh>
      {d.live.status === "alert" && (
        <mesh ref={ring} rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.03, 0]}>
          <ringGeometry args={[1.0, 1.1, 64]} />
          <meshBasicMaterial color="#ef4444" transparent opacity={0.6} />
        </mesh>
      )}
      <group onClick={(e) => { e.stopPropagation(); onSelect(d.id); }}>
        <Badge icon={DEVICE_ICON[d.kind] ?? "Cpu"} ring={color} position={[0, hub ? 2.2 : 1.9, 0]} scale={hub ? 1.6 : 1.25} />
      </group>
      {d.mitigations.length > 0 && (
        <mesh position={[0, hub ? 2.2 : 1.9, 0]} rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[hub ? 0.98 : 0.78, 0.035, 8, 64]} />
          <meshBasicMaterial color="#22d3ee" transparent opacity={0.85} />
        </mesh>
      )}
      <Label position={[0, hub ? 3.35 : 2.85, 0]} text={d.id} tone={selected ? "selected" : "default"} size={0.5} />
      {issues.slice(0, 2).map((txt, i) => (
        <Label key={txt} position={[0, (hub ? 3.85 : 3.35) + i * 0.5, 0]} text={`⚠ ${txt}`} tone="alert" size={0.46} />
      ))}
    </group>
  );
}

function Packets({ from, to, color, speed, count = 3 }: { from: THREE.Vector3; to: THREE.Vector3; color: string; speed: number; count?: number }) {
  const refs = useRef<(THREE.Mesh | null)[]>([]);
  const offsets = useMemo(() => Array.from({ length: count }, (_, i) => i / count), [count]);
  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    offsets.forEach((o, i) => {
      const m = refs.current[i];
      if (!m) return;
      const p = (o + t * speed) % 1;
      m.position.lerpVectors(from, to, p);
      m.position.y += Math.sin(p * Math.PI) * 0.5;
    });
  });
  return (
    <>
      {offsets.map((_, i) => (
        <mesh key={i} ref={(el) => { refs.current[i] = el; }}>
          <sphereGeometry args={[0.08, 10, 10]} />
          <meshBasicMaterial color={color} />
        </mesh>
      ))}
    </>
  );
}

function Persona({ kind, position, targets, label }: {
  kind: "adversary" | "analyst"; position: [number, number, number]; targets: SimDevice[]; label: string;
}) {
  const src = new THREE.Vector3(position[0], 1.6, position[2]);
  const adversary = kind === "adversary";
  return (
    <group>
      <mesh position={[position[0], 0.1, position[2]]}>
        <cylinderGeometry args={[0.9, 1.0, 0.2, 48]} />
        <meshStandardMaterial color="#111c33" emissive={adversary ? "#ef4444" : "#22d3ee"} emissiveIntensity={0.5} />
      </mesh>
      <Badge icon={PERSONA_ICON[kind]} ring={adversary ? "#ef4444" : "#22d3ee"} fill={adversary ? "#2a0a10" : "#062430"}
        position={[position[0], 1.7, position[2]]} scale={1.45} />
      <Label position={[position[0], 2.85, position[2]]} text={label} tone={adversary ? "alert" : "analyst"} size={0.42} />
      {targets.map((d) => {
        const dst = new THREE.Vector3(d.position[0], 1.6, d.position[1]);
        const quantum = d.active_attacks.some((a) => QUANTUM_ATTACKS.has(a));
        const c = adversary ? (quantum ? "#c084fc" : "#ef4444") : "#22d3ee";
        return (
          <group key={d.id}>
            <Line points={[src, dst]} color={c} lineWidth={1.4} dashed dashSize={0.4} gapSize={0.25} transparent opacity={0.85} />
            <Packets from={src} to={dst} color={c} speed={adversary ? 0.45 : 0.7} count={2} />
          </group>
        );
      })}
    </group>
  );
}

export function FleetScene({ devices, selected, assessing, onSelect }: {
  devices: SimDevice[]; selected: string | null; assessing?: string | null; onSelect: (id: string) => void;
}) {
  const hub = devices.find((d) => d.shape === "hub") ?? devices[0];
  const attacked = devices.filter((d) => d.active_attacks.length > 0);
  const watched = devices.filter((d) => d.id === assessing);
  const [ready, setReady] = useState(false);
  return (
    <Canvas shadows={{ type: THREE.PCFShadowMap }} camera={{ position: [0, 16, 19], fov: 42 }} onCreated={() => setReady(true)}
      gl={{ antialias: true, preserveDrawingBuffer: true }} data-testid="fleet-canvas" data-ready={ready}>
      <color attach="background" args={["#050913"]} />
      <fog attach="fog" args={["#050913", 30, 60]} />
      <ambientLight intensity={0.5} />
      <directionalLight position={[8, 14, 6]} intensity={1.1} />
      <pointLight position={[0, 6, 0]} intensity={30} color="#38bdf8" distance={18} />
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[44, 32]} />
        <meshStandardMaterial color="#0a1222" roughness={0.9} />
      </mesh>
      <gridHelper args={[44, 44, "#1e3a5f", "#13213a"]} position={[0, 0.01, 0]} />
      {hub && devices.filter((d) => d.id !== hub.id).map((d) => {
        const a = new THREE.Vector3(d.position[0], 0.3, d.position[1]);
        const b = new THREE.Vector3(hub.position[0], 0.3, hub.position[1]);
        const net = d.active_attacks.some((x) => NETWORK_ATTACKS.has(x));
        return (
          <group key={d.id}>
            <Line points={[a, b]} color={STATUS_COLOR[d.live.status]} lineWidth={1} transparent opacity={0.35} />
            <Packets from={a} to={b} color={net ? "#ef4444" : "#7dd3fc"} speed={net ? 1.4 : 0.35} count={net ? 6 : 2} />
          </group>
        );
      })}
      {devices.map((d) => <DeviceNode key={d.id} d={d} selected={selected === d.id} assessing={assessing === d.id} onSelect={onSelect} />)}
      <Persona kind="analyst" position={ANALYST} targets={watched} label="Security analyst · SafeGuard agents" />
      {attacked.length > 0 && <Persona kind="adversary" position={ADVERSARY} targets={attacked} label="Adversary (simulated)" />}
      <OrbitControls enablePan maxPolarAngle={Math.PI / 2.2} minDistance={8} maxDistance={42} />
    </Canvas>
  );
}
