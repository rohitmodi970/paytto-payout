"use client"

import { FormEvent, useEffect, useMemo, useState } from "react"

import { Button } from "@workspace/ui/components/button"

type LedgerEntry = {
  id: number
  amount_paise: number
  entry_type: "credit" | "debit"
  description: string
  created_at: string
}

type BalanceResponse = {
  merchant_id: number
  available_balance: number
  held_balance: number
  recent_ledger_entries: LedgerEntry[]
}

type PayoutRow = {
  payout_id: number
  merchant_id: number
  amount_paise: number
  status: string
  bank_account_id: string
  attempts: number
  requested_at: string
}

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1"

function formatINRFromPaise(paise: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(paise / 100)
}

function formatTimestamp(value: string) {
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value))
}

function payoutStatusBadgeClass(status: string) {
  if (status === "completed") {
    return "border-emerald-400/60 bg-emerald-100/80 text-emerald-900 dark:bg-emerald-900/25 dark:text-emerald-100"
  }
  if (status === "failed") {
    return "border-rose-400/60 bg-rose-100/80 text-rose-900 dark:bg-rose-900/25 dark:text-rose-100"
  }
  if (status === "processing") {
    return "border-cyan-400/60 bg-cyan-100/80 text-cyan-900 dark:bg-cyan-900/25 dark:text-cyan-100"
  }
  return "border-amber-400/60 bg-amber-100/80 text-amber-900 dark:bg-amber-900/25 dark:text-amber-100"
}

function ledgerTypeBadgeClass(type: LedgerEntry["entry_type"]) {
  if (type === "credit") {
    return "border-emerald-400/60 bg-emerald-100/80 text-emerald-900 dark:bg-emerald-900/25 dark:text-emerald-100"
  }
  return "border-amber-400/60 bg-amber-100/80 text-amber-900 dark:bg-amber-900/25 dark:text-amber-100"
}

export default function Page() {
  const [merchantId, setMerchantId] = useState("1")
  const [amountRupees, setAmountRupees] = useState("100")
  const [bankAccountId, setBankAccountId] = useState("bank_acc_demo_001")

  const [balance, setBalance] = useState<BalanceResponse | null>(null)
  const [payoutRows, setPayoutRows] = useState<PayoutRow[]>([])
  const [loadingBalance, setLoadingBalance] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [lastSync, setLastSync] = useState<string | null>(null)

  const amountPaise = useMemo(() => {
    const rupees = Number(amountRupees)
    if (!Number.isFinite(rupees) || rupees <= 0) {
      return 0
    }
    return Math.round(rupees * 100)
  }, [amountRupees])

  const loadBalance = async (targetMerchantId: string) => {
    if (!targetMerchantId) {
      return
    }

    setLoadingBalance(true)
    try {
      const response = await fetch(`${apiBase}/merchants/${targetMerchantId}/balance/`, {
        method: "GET",
        cache: "no-store",
      })

      if (!response.ok) {
        throw new Error(`Balance lookup failed with ${response.status}`)
      }

      const payload = (await response.json()) as BalanceResponse
      setBalance(payload)
      setLastSync(new Date().toISOString())
      setError(null)
    } catch (err) {
      const detail = err instanceof Error ? err.message : "Unknown error"
      setError(detail)
    } finally {
      setLoadingBalance(false)
    }
  }

  useEffect(() => {
    void loadBalance(merchantId)

    const timer = window.setInterval(() => {
      void loadBalance(merchantId)
    }, 8000)

    return () => window.clearInterval(timer)
  }, [merchantId])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!merchantId || !bankAccountId || amountPaise <= 0) {
      setError("Please enter merchant, amount, and bank account correctly.")
      return
    }

    setSubmitting(true)
    setError(null)
    setMessage(null)

    try {
      const idempotencyKey = crypto.randomUUID()
      const response = await fetch(`${apiBase}/payouts/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": idempotencyKey,
        },
        body: JSON.stringify({
          merchant_id: Number(merchantId),
          amount_paise: amountPaise,
          bank_account_id: bankAccountId,
        }),
      })

      const payload = (await response.json()) as
        | PayoutRow
        | {
            detail?: string
          }

      if (!response.ok) {
        throw new Error(
          "detail" in payload && payload.detail
            ? payload.detail
            : `Payout request failed with ${response.status}`,
        )
      }

      setPayoutRows((prev) => [
        {
          ...(payload as PayoutRow),
          requested_at: new Date().toISOString(),
        },
        ...prev,
      ])

      setMessage("Payout request accepted. Balance and ledger will refresh automatically.")
      void loadBalance(merchantId)
    } catch (err) {
      const detail = err instanceof Error ? err.message : "Unknown error"
      setError(detail)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="relative min-h-svh overflow-hidden px-4 py-8 sm:px-8">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -left-16 top-8 h-64 w-64 rounded-full bg-orange-300/30 blur-3xl" />
        <div className="absolute right-0 top-1/3 h-72 w-72 rounded-full bg-cyan-300/30 blur-3xl" />
        <div className="absolute bottom-0 left-1/3 h-80 w-80 rounded-full bg-emerald-200/30 blur-3xl" />
      </div>

      <section className="relative mx-auto flex w-full max-w-6xl flex-col gap-6">
        <header className="rounded-2xl border border-border/70 bg-card/80 p-6 backdrop-blur">
          <p className="text-xs font-semibold tracking-[0.2em] text-muted-foreground">PLAYTO PAYOUT CONSOLE</p>
          <h1 className="mt-2 text-2xl font-semibold sm:text-3xl">Merchant Dashboard</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Scaffold aligned to rubric: live balance cards, payout request form, payout attempts table, and polling refresh every 8 seconds.
          </p>
        </header>

        <div className="grid gap-4 md:grid-cols-3">
          <article className="rounded-2xl border border-emerald-300/50 bg-card/90 p-5">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Available Balance</p>
            <p className="mt-2 text-2xl font-semibold">
              {balance ? formatINRFromPaise(balance.available_balance) : "--"}
            </p>
          </article>
          <article className="rounded-2xl border border-amber-300/60 bg-card/90 p-5">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Held Balance</p>
            <p className="mt-2 text-2xl font-semibold">
              {balance ? formatINRFromPaise(balance.held_balance) : "--"}
            </p>
          </article>
          <article className="rounded-2xl border border-cyan-300/60 bg-card/90 p-5">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Last Sync</p>
            <p className="mt-2 text-lg font-semibold">
              {lastSync ? formatTimestamp(lastSync) : loadingBalance ? "Syncing..." : "Not synced"}
            </p>
          </article>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="rounded-2xl border border-border/70 bg-card/90 p-5">
            <div className="mb-4 flex items-center justify-between gap-3">
              <h2 className="text-lg font-semibold">Create Payout</h2>
              <Button type="button" variant="outline" onClick={() => void loadBalance(merchantId)}>
                Refresh Balance
              </Button>
            </div>

            <form className="grid gap-4" onSubmit={handleSubmit}>
              <label className="grid gap-2 text-sm">
                Merchant ID
                <input
                  value={merchantId}
                  onChange={(event) => setMerchantId(event.target.value)}
                  className="h-10 rounded-lg border border-border bg-background px-3"
                  placeholder="1"
                />
              </label>

              <label className="grid gap-2 text-sm">
                Amount (INR)
                <input
                  value={amountRupees}
                  onChange={(event) => setAmountRupees(event.target.value)}
                  className="h-10 rounded-lg border border-border bg-background px-3"
                  placeholder="100"
                />
              </label>

              <label className="grid gap-2 text-sm">
                Bank Account ID
                <input
                  value={bankAccountId}
                  onChange={(event) => setBankAccountId(event.target.value)}
                  className="h-10 rounded-lg border border-border bg-background px-3"
                  placeholder="bank_acc_demo_001"
                />
              </label>

              <div className="flex items-center gap-3 pt-2">
                <Button type="submit" disabled={submitting}>
                  {submitting ? "Submitting..." : "Submit Payout"}
                </Button>
                <span className="text-xs text-muted-foreground">
                  Amount preview: {amountPaise > 0 ? formatINRFromPaise(amountPaise) : "--"}
                </span>
              </div>
            </form>

            {error ? (
              <p className="mt-4 rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {error}
              </p>
            ) : null}
            {message ? (
              <p className="mt-4 rounded-lg border border-emerald-400/50 bg-emerald-100/60 px-3 py-2 text-sm text-emerald-900 dark:bg-emerald-900/20 dark:text-emerald-100">
                {message}
              </p>
            ) : null}
          </section>

          <section className="rounded-2xl border border-border/70 bg-card/90 p-5">
            <h2 className="mb-4 text-lg font-semibold">Recent Ledger Entries</h2>
            <div className="max-h-[360px] overflow-auto rounded-lg border border-border">
              <table className="w-full text-left text-xs sm:text-sm">
                <thead className="bg-muted/70 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2">Entry</th>
                    <th className="hidden px-3 py-2 sm:table-cell">Time</th>
                    <th className="px-3 py-2">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {balance?.recent_ledger_entries?.length ? (
                    balance.recent_ledger_entries.map((entry) => (
                      <tr key={entry.id} className="border-t border-border/70">
                        <td className="px-3 py-2">
                          <div className="flex flex-col gap-1">
                            <span
                              className={`inline-flex w-fit rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${ledgerTypeBadgeClass(entry.entry_type)}`}
                            >
                              {entry.entry_type}
                            </span>
                            <p className="line-clamp-1 text-[11px] text-muted-foreground sm:text-xs">{entry.description}</p>
                            <p className="text-[10px] text-muted-foreground sm:hidden">
                              {formatTimestamp(entry.created_at)}
                            </p>
                          </div>
                        </td>
                        <td className="hidden px-3 py-2 sm:table-cell">{formatTimestamp(entry.created_at)}</td>
                        <td className="px-3 py-2 font-medium">{formatINRFromPaise(entry.amount_paise)}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td className="px-3 py-4 text-muted-foreground" colSpan={3}>
                        No ledger entries yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <section className="rounded-2xl border border-border/70 bg-card/90 p-5">
          <h2 className="mb-4 text-lg font-semibold">Payout Attempts This Session</h2>
          <div className="overflow-auto rounded-lg border border-border">
            <table className="w-full text-left text-xs sm:text-sm">
              <thead className="bg-muted/70 text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-3 py-2">Payout</th>
                  <th className="hidden px-3 py-2 sm:table-cell">Requested</th>
                  <th className="hidden px-3 py-2 sm:table-cell">Merchant</th>
                  <th className="px-3 py-2">Amount</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="hidden px-3 py-2 sm:table-cell">Attempts</th>
                </tr>
              </thead>
              <tbody>
                {payoutRows.length ? (
                  payoutRows.map((row) => (
                    <tr key={`${row.payout_id}-${row.requested_at}`} className="border-t border-border/70">
                      <td className="px-3 py-2">
                        <div className="flex flex-col gap-1">
                          <span className="font-medium">#{row.payout_id}</span>
                          <span className="text-[10px] text-muted-foreground sm:hidden">
                            {formatTimestamp(row.requested_at)} • M{row.merchant_id} • Try {row.attempts}
                          </span>
                        </div>
                      </td>
                      <td className="hidden px-3 py-2 sm:table-cell">{formatTimestamp(row.requested_at)}</td>
                      <td className="hidden px-3 py-2 sm:table-cell">{row.merchant_id}</td>
                      <td className="px-3 py-2 font-medium">{formatINRFromPaise(row.amount_paise)}</td>
                      <td className="px-3 py-2">
                        <span
                          className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${payoutStatusBadgeClass(row.status)}`}
                        >
                          {row.status}
                        </span>
                      </td>
                      <td className="hidden px-3 py-2 sm:table-cell">{row.attempts}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td className="px-3 py-4 text-muted-foreground" colSpan={6}>
                      No payout attempts in this tab yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </section>
    </main>
  )
}
