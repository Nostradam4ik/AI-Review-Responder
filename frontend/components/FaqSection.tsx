"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

const FAQS = [
  {
    q: "Est-ce que ça fonctionne avec Google Business Profile ?",
    a: "Oui, l'outil se connecte directement à votre compte Google Business Profile et synchronise automatiquement vos avis.",
  },
  {
    q: "Puis-je modifier les réponses générées par l'IA ?",
    a: "Absolument. Chaque réponse générée peut être modifiée avant publication. Vous gardez le contrôle total.",
  },
  {
    q: "Que se passe-t-il après les 14 jours d'essai ?",
    a: "Votre compte reste actif mais les fonctions de réponse sont désactivées. Vous choisissez un plan pour continuer.",
  },
  {
    q: "Est-ce que je peux gérer plusieurs restaurants ?",
    a: "Oui. Le plan Pro permet 3 établissements, le plan Agency jusqu'à 10.",
  },
  {
    q: "Comment fonctionne la facturation ?",
    a: "Paiement mensuel par carte via Stripe. Annulation possible à tout moment, sans engagement.",
  },
];

export function FaqSection() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  const toggle = (i: number) =>
    setOpenIndex(openIndex === i ? null : i);

  return (
    <section className="max-w-3xl mx-auto px-6 py-24">
      <div className="text-center mb-12">
        <h2 className="text-3xl font-bold text-white">Questions fréquentes</h2>
      </div>

      <div className="space-y-3">
        {FAQS.map((faq, i) => (
          <div
            key={i}
            className="bg-[#111118] border border-[#2A2A3E] rounded-xl overflow-hidden"
          >
            <button
              onClick={() => toggle(i)}
              className="w-full flex items-center justify-between gap-4 px-6 py-4 text-left text-sm font-medium text-white hover:text-indigo-300 transition-colors"
            >
              <span>{faq.q}</span>
              {openIndex === i ? (
                <ChevronUp className="w-4 h-4 shrink-0 text-indigo-400" />
              ) : (
                <ChevronDown className="w-4 h-4 shrink-0 text-slate-500" />
              )}
            </button>

            {openIndex === i && (
              <div className="px-6 pb-5 text-sm text-slate-400 leading-relaxed border-t border-[#2A2A3E] pt-4">
                {faq.a}
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
