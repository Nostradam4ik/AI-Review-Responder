"use client";
import { useEffect, useState } from "react";
import { billingApi } from "@/lib/api";

export interface SubscriptionState {
  isTrialExpired: boolean;
  isTrial: boolean;
  trialDaysRemaining: number;
  isActive: boolean;
  loading: boolean;
}

export function useSubscription(): SubscriptionState {
  const [state, setState] = useState<SubscriptionState>({
    isTrialExpired: false,
    isTrial: false,
    trialDaysRemaining: 0,
    isActive: true,
    loading: true,
  });

  useEffect(() => {
    billingApi
      .status()
      .then((data) => {
        const isTrialExpired =
          data.is_trial === true && (data.trial_days_remaining ?? 1) <= 0;

        setState({
          isTrialExpired,
          isTrial: data.is_trial ?? false,
          trialDaysRemaining: data.trial_days_remaining ?? 0,
          isActive: data.subscription?.status === "active",
          loading: false,
        });
      })
      .catch(() => {
        setState((s) => ({ ...s, loading: false }));
      });
  }, []);

  return state;
}
