import ProgressPanel from "@/components/drive/ProgressPanel";
import { FINISHING_FRACTION, type BatchProgress } from "@/lib/batchUpload";

export default function UploadProgress({
  progress,
}: {
  progress: BatchProgress;
}) {
  return (
    <ProgressPanel
      title={`Uploading ${progress.finished}/${progress.total}`}
      detail={`${progress.percent}%`}
      percent={progress.percent}
      items={progress.active.map(e => ({
        name: e.name,
        percent: Math.round(e.fraction * 100),
        ...(e.fraction >= FINISHING_FRACTION && { label: "Finishing…" }),
      }))}
    />
  );
}
