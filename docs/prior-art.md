# Prior art

What earlier work says about pooling several answers from one model, and what it predicts for Jev. Citations
were checked against arXiv, ACL or publisher pages on 2026-10-01 unless marked *(unchecked)*.

## The short version

Pooling helps only when the pooled answers make different mistakes. Averaging removes noise, not bias.
Every line of work below finds the same thing: the gain comes from diversity among members, and identical
repeats of one judgment add almost nothing. So the question for Jev is not "is pooling cheap?" (it is, at
about 175 input tokens per extra copy) but "do copies disagree, and on items where they disagree, is the
majority right?"

## Ensemble theory

- **Condorcet jury theorem with correlated voters.** Boland, P.J. (1989), *The Statistician* 38(3):181–189;
  Ladha, K.K. (1992), *American Journal of Political Science* 36(3):617–634. Majority vote gains depend on
  how dependent the voters are. With pairwise correlation ρ, k voters count as about k / (1 + (k − 1)ρ).
- **Ambiguity decomposition.** Krogh, A. & Vedelsby, J. (1995), *NIPS 7*:231–238. Ensemble error equals
  average member error minus the members' spread. No spread, no gain.
- **Bagging.** Breiman, L. (1996), *Machine Learning* 24:123–140. Helps unstable predictors; can slightly hurt
  stable ones.
- **Combining rules.** Kittler, J., Hatef, M., Duin, R.P.W. & Matas, J. (1998), "On combining classifiers,"
  *IEEE TPAMI* 20(3):226–239. Derives the sum (mean), product, vote and other rules; the sum rule is the most
  robust to noisy probability estimates. This is the citation for averaging probabilities ("soft voting").
  Textbook: Kuncheva, L.I., *Combining Pattern Classifiers* (Wiley, 2nd ed. 2014).
- **Why ensembles work.** Dietterich, T.G. (2000), "Ensemble methods in machine learning," *MCS 2000*,
  LNCS 1857:1–15. Members must be accurate and diverse.
- **Measuring diversity.** Kuncheva, L.I. & Whitaker, C.J. (2003), *Machine Learning* 51:181–207.

## Pooling probability forecasts

- Clemen, R.T. (1989), "Combining forecasts," *International Journal of Forecasting* 5(4):559–583. Simple
  averages reliably help across about 200 studies.
- Genest, C. & Zidek, J.V. (1986), *Statistical Science* 1(1):114–135. Linear versus logarithmic pools
  *(page details unchecked)*.
- Ranjan, R. & Gneiting, T. (2010), "Combining probability forecasts," *JRSS-B* 72(1):71–91. A linear pool of
  calibrated forecasts is underconfident, so pooled probabilities need their own calibration check.
- Satopää, V.A. et al. (2014), *International Journal of Forecasting* 30(2):344–356; Baron, J. et al. (2014),
  *Decision Analysis* 11(2):133–145. Averaging then extremizing helps when forecasters hold partly
  independent information; it does not apply to identical copies *(figures unchecked)*.

## One mind asked twice

The closest human analogy to identical copies in one request.

- Vul, E. & Pashler, H. (2008), "Measuring the crowd within," *Psychological Science* 19(7):645–647. A
  person's immediate second guess was worth about a tenth of another person's.
- Herzog, S.M. & Hertwig, R. (2009), "The wisdom of many in one mind," *Psychological Science* 20(2):231–237.
  Plain re-asking gained 0.3 points; asking people to assume their first answer was wrong gained 4.1; a second
  person gained 7.1. Gains come from prompts that draw on different information.

## Repeated LLM sampling

- Wang, X. et al. (2023), "Self-consistency improves chain of thought reasoning in language models,"
  *ICLR 2023*, arXiv 2203.11171. Voting over sampled reasoning paths: GSM8K +17.9, StrategyQA +6.4,
  ARC-Challenge +3.9 points. The diversity comes from sampling different reasoning, which a probability
  readout does not have.
- Li, J. et al. (2024), "More agents is all you need," *TMLR*, arXiv 2402.05120.
- Chen, L. et al. (2024), "Are more LLM calls all you need? Towards the scaling properties of compound AI
  systems," *NeurIPS 2024*, arXiv 2403.02419. Voting helps items the model usually gets right and hurts items
  it usually gets wrong, so gains can rise and then fall with more calls. Results must be split by difficulty.
- Brown, B. et al. (2024), "Large Language Monkeys," arXiv 2407.21787. Without a verifier, voting plateaus.

## Varying the prompt

- Jiang, Z. et al. (2020), "How can we know what language models know?" *TACL* 8, arXiv 1911.12543. Paraphrase
  ensembles raised LAMA accuracy from 31.1% to 39.6%.
- Arora, S. et al. (2023), "Ask me anything," *ICLR 2023*, arXiv 2210.02441. Several prompt formats combined
  by weak supervision, +10.2% over few-shot.
- Li, Y. et al. (2023), DiVeRSE, *ACL 2023*, arXiv 2206.02336. Diverse prompts plus a verifier.
- Zhao, T.Z. et al. (2021), "Calibrate before use," *ICML 2021*, arXiv 2102.09690; Lu, Y. et al. (2022),
  "Fantastically ordered prompts," *ACL 2022*, arXiv 2104.08786; Sclar, M. et al. (2024), *ICLR 2024*,
  arXiv 2310.11324. Format and order alone move accuracy a great deal.
- Option order: Pezeshkpour, P. & Hruschka, E. (2024), *Findings of NAACL*, arXiv 2308.11483; Zheng, C. et al.
  (2024), "Large language models are not robust multiple choice selectors," *ICLR 2024*, arXiv 2309.03882;
  Tang, R. et al. (2024), "Found in the middle," *NAACL 2024*, arXiv 2310.07712 (shuffle, then pool: +7–18%
  on ranking).

## Several questions in one request

- Cheng, Z., Kasai, J. & Yu, T. (2023), "Batch prompting," *EMNLP 2023 Industry*, arXiv 2301.08721.
- Lin, J. et al. (2023), "BatchPrompt," arXiv 2309.00384 (preprint). Re-asks a batch with items reordered and
  votes across rounds. Gains come from changing positions, not from repeating the same layout.
- Wang, Z., Kodner, J. & Rambow, O. (2025), "Evaluating LLMs with multiple problems at once," arXiv 2406.10786.

## Uncertainty from disagreement

- Lakshminarayanan, B. et al. (2017), deep ensembles, *NeurIPS 2017*; Gal, Y. & Ghahramani, Z. (2016), MC
  dropout, *ICML 2016*; Ovadia, Y. et al. (2019), *NeurIPS 2019*. These need independently trained members or
  randomness at inference.
- Kuhn, L. et al. (2023), semantic entropy, *ICLR 2023*, arXiv 2302.09664; Xiong, M. et al. (2024),
  *ICLR 2024*, arXiv 2306.13063.
- Geifman, Y. & El-Yaniv, R. (2017), selective classification, *NeurIPS 2017*.

## Jev

September 2026 preprints, read from abstracts or HTML only *(unchecked in full)*: Deußer et al., arXiv
2609.37647 (benchmark; questions in a request "share the state but are answered independently"); Xu,
"JevOut," arXiv 2609.30243 (short added context flipped 61.4% of correct items, a caution for paraphrase arms).

Sibling projects: Hard-Decisions (ProofWriter accuracy and retest), Biased-Decisions (ask-twice flips 0.4–0.6%;
reversing option order flips 1.0–2.8%), Jev-Calibration (averaging three framings gave the best raw ECE, 0.064),
Decision Models Are Not Calculators (exact repeats nearly identical).

## Statistics

McNemar, Q. (1947), *Psychometrika* 12(2):153–157; Dietterich, T.G. (1998), *Neural Computation*
10(7):1895–1923; Koehn, P. (2004), paired bootstrap, *EMNLP*; Card, D. et al. (2020), "With little power comes
great responsibility," *EMNLP*; Gwet, K.L. (2008), AC1, *British Journal of Mathematical and Statistical
Psychology* 61(1):29–48.

Power: with discordant share ψ and accuracy difference δ, a paired test at α = 0.05 and 80% power needs about
n ≈ 7.85 ψ / δ² items. With ψ ≈ 2% (ProofWriter), a 1-point gain needs about 1,600 items.

## Not used

Perplexity's source for soft voting, a Universidad de Chile predictive-maintenance thesis, could not be found
and would not be a suitable source for a basic method; Kittler et al. (1998) replaces it. Cameron Wolfe's
"Prompt Ensembles Make LLMs More Reliable" (Substack, 2023) is an accurate review of AMA and DiVeRSE; cite those.
