"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { api, ImageOut, Inspection, OrderDetail, OrderItem, Product, SampleImage } from "@/lib/api";
import RiskBadge from "@/components/RiskBadge";
import InspectionStatusBadge, { ConfidenceLabel } from "@/components/InspectionStatusBadge";
import QualityScoreGauge from "@/components/QualityScoreGauge";
import { LoadingState, ErrorState } from "@/components/States";

type Step = "loading" | "already-done" | "replaced" | "capture" | "quality-poor" | "analyzing" | "result" | "accepted" | "replace" | "error";

export default function InspectionPage() {
  const params = useParams();
  const router = useRouter();
  const orderId = Number(params.orderId);
  const itemId = Number(params.itemId);

  const [step, setStep] = useState<Step>("loading");
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [item, setItem] = useState<OrderItem | null>(null);
  const [samples, setSamples] = useState<SampleImage[]>([]);
  const [inspectionId, setInspectionId] = useState<number | null>(null);
  const [pendingImage, setPendingImage] = useState<ImageOut | null>(null);
  const [result, setResult] = useState<Inspection | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [replacementProductId, setReplacementProductId] = useState<number | null>(null);
  const [escalate, setEscalate] = useState(false);
  const [busy, setBusy] = useState(false);

  const cameraInputRef = useRef<HTMLInputElement>(null);
  const uploadInputRef = useRef<HTMLInputElement>(null);

  async function load() {
    try {
      const o = await api.getOrder(orderId);
      setOrder(o);
      const it = o.items.find((i) => i.id === itemId) || null;
      setItem(it);
      if (!it) {
        setStep("error");
        setErrorMsg("Order item not found.");
        return;
      }
      if (it.replaced) {
        setStep("replaced");
        return;
      }
      if (it.quality_check_status === "PASSED" || it.quality_check_status === "FAILED") {
        setStep("already-done");
        return;
      }

      // Reuse a PENDING inspection already created for this item (e.g. by
      // replace_item()) instead of creating a duplicate.
      const existing = await api.listInspections({ order_item_id: String(itemId), status: "PENDING" });
      if (existing.length > 0) setInspectionId(existing[0].inspectionId);

      setStep("capture");
    } catch (e) {
      setStep("error");
      setErrorMsg(String(e));
    }
  }

  useEffect(() => {
    load();
    api.listSampleImages().then(setSamples).catch(() => {});
  }, [orderId, itemId]);

  async function handleImageReady(image: ImageOut) {
    if (image.imageQuality.status === "poor") {
      setPendingImage(image);
      setStep("quality-poor");
      return;
    }
    await runInspection(image);
  }

  async function runInspection(image: ImageOut) {
    setStep("analyzing");
    setErrorMsg(null);
    try {
      let insp: Inspection;
      if (inspectionId) {
        insp = await api.attachImage(inspectionId, image.id);
      } else {
        insp = await api.createInspection(orderId, itemId, image.id);
      }
      setInspectionId(insp.inspectionId);
      const analyzed = await api.analyzeInspection(insp.inspectionId);
      setResult(analyzed);
      setStep("result");
    } catch (e) {
      setErrorMsg(String(e));
      setStep("error");
    }
  }

  async function onFileSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setBusy(true);
    try {
      const image = await api.uploadImageFile(file);
      await handleImageReady(image);
    } catch (err) {
      setErrorMsg("Unable to upload image. Try again.");
      setStep("error");
    } finally {
      setBusy(false);
    }
  }

  async function useSample(key: string) {
    setBusy(true);
    try {
      const image = await api.uploadSampleImage(key);
      await handleImageReady(image);
    } catch (err) {
      setErrorMsg(String(err));
      setStep("error");
    } finally {
      setBusy(false);
    }
  }

  async function accept() {
    if (!result) return;
    setBusy(true);
    try {
      await api.acceptInspection(result.inspectionId);
      setStep("accepted");
    } catch (e) {
      setErrorMsg(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function reject() {
    if (!result) return;
    setBusy(true);
    try {
      await api.rejectInspection(result.inspectionId);
      const cat = item?.product.category;
      const list = await api.listProducts();
      setProducts(list.filter((p) => p.category === cat && p.id !== item?.product.id));
      setStep("replace");
    } catch (e) {
      setErrorMsg(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function rescan() {
    if (!result) return;
    setBusy(true);
    try {
      const fresh = await api.reinspect(result.inspectionId);
      setInspectionId(fresh.inspectionId);
      setResult(null);
      setPendingImage(null);
      setStep("capture");
    } catch (e) {
      setErrorMsg(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function confirmReplacement() {
    if (!result || !replacementProductId) return;
    setBusy(true);
    try {
      const res = await api.replaceItem(result.inspectionId, replacementProductId, "Failed AI quality inspection");
      setEscalate(res.escalate);
      if (res.escalate) {
        setTimeout(() => router.push(`/inspection/${orderId}/${res.newOrderItem.id}`), 2500);
      } else {
        router.push(`/inspection/${orderId}/${res.newOrderItem.id}`);
      }
    } catch (e) {
      setErrorMsg(String(e));
    } finally {
      setBusy(false);
    }
  }

  if (step === "loading") return <LoadingState label="Loading inspection..." />;
  if (step === "error") return <ErrorState message={errorMsg || "Something went wrong."} />;

  const header = order && item && (
    <div className="mb-6">
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-xl font-bold">AI Quality Inspection</h1>
        <span className="text-[#8b93ab]">·</span>
        <Link href={`/orders/${orderId}`} className="text-[#4f7cff] hover:underline text-sm">
          {order.order_code}
        </Link>
      </div>
      <div className="flex items-center gap-4 mt-2 text-sm text-[#c3c9dc]">
        <span>
          {item.product.emoji} {item.product.name} · Qty {item.quantity}
        </span>
        <span className="flex items-center gap-1">
          Risk: <RiskBadge level={order.risk_level} />
        </span>
      </div>
    </div>
  );

  if (step === "replaced" && item) {
    return (
      <div className="max-w-xl">
        {header}
        <div className="card p-6">
          <p className="text-sm text-[#c3c9dc] mb-3">This item was already replaced during inspection.</p>
          <Link href={`/inspection/${orderId}/${item.replaced_by_item_id}`} className="btn btn-primary inline-flex">
            Go to replacement inspection →
          </Link>
        </div>
      </div>
    );
  }

  if (step === "already-done" && item) {
    return (
      <div className="max-w-xl">
        {header}
        <div className="card p-6 text-center space-y-3">
          <div className="text-3xl">{item.quality_check_status === "PASSED" ? "✅" : "⚠️"}</div>
          <p className="font-semibold">
            Quality check {item.quality_check_status === "PASSED" ? "completed" : "failed"} for this item.
          </p>
          <Link href="/picker" className="btn btn-primary inline-flex">
            Back to Picker
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-xl">
      {header}

      {step === "capture" && (
        <div className="card p-6 space-y-5">
          <div className="border-2 border-dashed border-[#2c3550] rounded-xl h-56 flex items-center justify-center text-[#5b6480] text-sm">
            {busy ? "Uploading..." : "PRODUCT IMAGE"}
          </div>

          <ul className="text-xs text-[#8b93ab] space-y-1">
            <li>✓ Place the product inside the frame</li>
            <li>✓ Ensure sufficient lighting</li>
            <li>✓ Show the product surface clearly</li>
            <li>✓ Avoid excessive blur</li>
          </ul>

          <div className="flex gap-3">
            <button className="btn btn-primary flex-1" disabled={busy} onClick={() => cameraInputRef.current?.click()}>
              Capture Image
            </button>
            <button className="btn btn-secondary flex-1" disabled={busy} onClick={() => uploadInputRef.current?.click()}>
              Upload Image
            </button>
          </div>
          <input ref={cameraInputRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={onFileSelected} />
          <input ref={uploadInputRef} type="file" accept="image/*" className="hidden" onChange={onFileSelected} />

          {samples.length > 0 && (
            <div>
              <div className="text-xs uppercase tracking-wide text-[#8b93ab] font-medium mb-2">
                Prototype Vision Simulation — try a sample image
              </div>
              <div className="flex gap-2 overflow-x-auto pb-1">
                {samples.map((s) => (
                  <button
                    key={s.key}
                    disabled={busy}
                    onClick={() => useSample(s.key)}
                    className="shrink-0 text-left border border-[#232b40] rounded-lg px-3 py-2 text-xs hover:border-[#4f7cff] disabled:opacity-50"
                    title={s.label}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {step === "quality-poor" && pendingImage && (
        <div className="card p-6 space-y-4">
          <div className="text-orange-400 font-semibold">⚠ Image quality insufficient</div>
          <ul className="text-sm space-y-1">
            {pendingImage.imageQuality.issues.map((issue, i) => (
              <li key={i}>• {issue}</li>
            ))}
          </ul>
          <p className="text-sm text-[#c3c9dc]">
            Please: improve lighting, move product closer, keep product centered, retake image.
          </p>
          <button className="btn btn-primary" onClick={() => setStep("capture")}>
            Retake Image
          </button>
        </div>
      )}

      {step === "analyzing" && (
        <div className="card p-10 text-center">
          <div className="animate-pulse text-[#c3c9dc]">Analyzing product quality…</div>
        </div>
      )}

      {step === "result" && result && (
        <div className="card p-6 space-y-5">
          <div className="text-xs text-[#5b6480] text-center">
            Prototype Vision Simulation ({result.modelVersion}) — visible quality inspection, not a certainty
          </div>
          <div className="flex flex-col items-center">
            <QualityScoreGauge score={result.qualityScore ?? 0} />
            <div className="mt-2">
              <InspectionStatusBadge status={result.inspectionStatus} />
            </div>
          </div>

          {result.mandatoryHumanReview && result.aiDecision === "PASS" && (
            <p className="text-xs text-amber-400 text-center">
              CRITICAL-risk order — human confirmation required even though AI found no defect.
            </p>
          )}

          {result.defects.length > 0 && (
            <div>
              <div className="text-xs uppercase tracking-wide text-[#8b93ab] font-medium mb-2">Detected Defect(s)</div>
              <ul className="space-y-2">
                {result.defects.map((d, i) => (
                  <li key={i} className="text-sm flex items-center justify-between border border-[#232b40] rounded-lg px-3 py-2">
                    <span className="capitalize">{d.description || d.type.replace("_", " ")}</span>
                    <span className="flex items-center gap-3 text-xs">
                      <ConfidenceLabel confidence={d.confidence} />
                      <span className="capitalize text-[#8b93ab]">{d.severity} severity</span>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="bg-[#1a2136] rounded-lg p-3 text-sm">
            <span className="text-[#8b93ab]">AI Recommendation: </span>
            {result.inspectionStatus === "PASS" && "No significant visible defects detected. Safe to continue."}
            {result.inspectionStatus === "REVIEW" && "Inspect the affected area before accepting this product."}
            {result.inspectionStatus === "REJECT" && "Recommend rejecting and selecting a replacement."}
          </div>

          <div className="flex gap-3">
            <button className="btn btn-primary flex-1" disabled={busy} onClick={accept}>
              Accept
            </button>
            <button className="btn btn-danger flex-1" disabled={busy} onClick={reject}>
              Reject
            </button>
            <button className="btn btn-secondary flex-1" disabled={busy} onClick={rescan}>
              Re-Scan
            </button>
          </div>
        </div>
      )}

      {step === "accepted" && result && (
        <div className="card p-6 text-center space-y-3">
          <div className="text-3xl">✓</div>
          <p className="font-semibold">Quality check completed</p>
          <p className="text-sm text-[#8b93ab]">
            Score: {Math.round(result.qualityScore ?? 0)} · Status: PASS
          </p>
          <Link href="/picker" className="btn btn-primary inline-flex">
            Back to Picker
          </Link>
        </div>
      )}

      {step === "replace" && (
        <div className="card p-6 space-y-4">
          <div className="text-red-400 font-semibold">⚠ Product Rejected</div>
          <p className="text-sm text-[#c3c9dc]">
            Reason: {result?.defects[0]?.description || "Visible defect detected"}
          </p>
          {escalate && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-400">
              Repeated inspection failures for this category — escalated to warehouse/QC manager.
            </div>
          )}
          <p className="text-sm">Action: please select a replacement.</p>
          <select
            className="w-full bg-[#0f1420] border border-[#232b40] rounded-lg px-3 py-2 text-sm"
            value={replacementProductId ?? ""}
            onChange={(e) => setReplacementProductId(Number(e.target.value))}
          >
            <option value="">Choose a replacement product…</option>
            {products.map((p) => (
              <option key={p.id} value={p.id}>
                {p.emoji} {p.name}
              </option>
            ))}
          </select>
          <button className="btn btn-primary w-full" disabled={!replacementProductId || busy} onClick={confirmReplacement}>
            Scan Replacement
          </button>
        </div>
      )}
    </div>
  );
}
