/**
 * Icon mapping (Lucide, ISC licence — https://lucide.dev). The same vector data is used by the
 * HTML UI (lucide-react) and rasterised into WebGL textures for the 3D scene.
 */
import { icons, type IconNode } from "lucide";

export const DEVICE_ICON: Record<string, keyof typeof icons> = {
  edge_gateway: "Router",
  infusion_pump: "Syringe",
  ecg_monitor: "HeartPulse",
  ventilator: "Wind",
  patient_wearable: "Watch",
  pacs_gateway: "ScanEye",
  ehr_api: "Database",
  clinical_ai: "Bot",
  ot_gateway: "Router",
  plc: "Cpu",
  scada_hmi: "Monitor",
  vibration_sensor: "Activity",
  robot_cell: "Factory",
};

export const PERSONA_ICON = { adversary: "Skull", analyst: "ShieldCheck" } as const;

function nodeToSvg(node: IconNode, color: string, size: number, strokeWidth = 2): string {
  const children = node
    .map(([tag, attrs]) => `<${tag} ${Object.entries(attrs).map(([k, v]) => `${k}="${v}"`).join(" ")}/>`)
    .join("");
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="${strokeWidth}" stroke-linecap="round" stroke-linejoin="round">${children}</svg>`;
}

const imageCache = new Map<string, Promise<HTMLImageElement>>();

/** Loads a Lucide icon as an <img> suitable for canvas drawing (cached). */
export function iconImage(name: keyof typeof icons, color: string, size = 96): Promise<HTMLImageElement> {
  const key = `${name}|${color}|${size}`;
  let p = imageCache.get(key);
  if (!p) {
    p = new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(nodeToSvg(icons[name] as IconNode, color, size))}`;
    });
    imageCache.set(key, p);
  }
  return p;
}
