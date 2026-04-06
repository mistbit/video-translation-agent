import { useEffect, useState } from 'react';

import { getActiveJobBundle } from './api';
import type { ActiveJobBundle } from './types';

type JobTarget = {
  jobId: string;
  artifactRoot: string;
} | null;

export function useJobPolling(target: JobTarget, loadErrorMessage: string) {
  const [data, setData] = useState<ActiveJobBundle | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!target) {
      setData(null);
      setError(null);
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    const load = async (showSpinner: boolean) => {
      if (showSpinner) {
        setIsLoading(true);
      }
      try {
        const bundle = await getActiveJobBundle(target.jobId, target.artifactRoot);
        if (cancelled) {
          return;
        }
        setData(bundle);
        setError(null);
      } catch (nextError) {
        if (cancelled) {
          return;
        }
        setError(
          nextError instanceof Error
            ? nextError.message
            : loadErrorMessage
        );
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    void load(true);
    const intervalId = window.setInterval(() => {
      void load(false);
    }, 5000);

    return () => {
      cancelled = true;
      if (intervalId !== undefined) {
        window.clearInterval(intervalId);
      }
    };
  }, [loadErrorMessage, target]);

  return { data, isLoading, error };
}
