import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Spinner } from "@/components/ui/spinner";

/**
 * Inline audio/video player. The file is served from an authenticated endpoint,
 * so we fetch it as a blob (with the bearer token) and play it via an object URL
 * rather than pointing the element straight at the URL.
 */
export function MediaPlayer({ url, kind }: { url: string; kind: "video" | "audio" }) {
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    let objUrl: string | undefined;
    setSrc(null);
    setFailed(false);
    api
      .get(url, { responseType: "blob" })
      .then((res) => {
        if (!active) return;
        objUrl = URL.createObjectURL(res.data as Blob);
        setSrc(objUrl);
      })
      .catch(() => active && setFailed(true));
    return () => {
      active = false;
      if (objUrl) URL.revokeObjectURL(objUrl);
    };
  }, [url]);

  if (failed) return <p className="text-xs text-destructive">Could not load media.</p>;
  if (!src)
    return (
      <div className="flex justify-center py-6">
        <Spinner />
      </div>
    );

  return kind === "video" ? (
    <video controls src={src} className="w-full rounded-lg border bg-black" />
  ) : (
    <audio controls src={src} className="w-full" />
  );
}
