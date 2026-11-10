"""
Hawk-Dove: an evolutionary game-theory simulation based on the passage in
"Deep Simplicity".

Numbers from the book
---------------------
  food is worth 50 points
  a threat display costs 10 points
  losing a fight costs 100 points (injury); winning a fight gains the food

Strategies
----------
  Dove  : never starts a fight, displays, runs away if attacked
  Hawk  : always fights, never displays
  Mixed : in every encounter acts like a hawk with probability p_hawk
          (chosen at random, no planning in advance)

Scenarios (python hawk_dove.py <name>)
--------------------------------------
  theory      payoff table, the ESS (5 doves : 7 hawks) and 6.25 pts/conflict
  doves       all-dove "Utopia", then a single mutant hawk arises
  hawks       all-hawk disaster, then a single mutant dove arises
  extinction  all-hawk population dies out ... unless there is free food
  welfare     the stable situation is not the best one (6.25 vs 15)
  mixed       5 doves:7 hawks  ==  everyone acting 5/12 dove, 7/12 hawk
  evolve      evolution discovers the mixed strategy on its own
  all         run everything
"""
from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from fractions import Fraction

FOOD = 50
DISPLAY_COST = 10
INJURY_COST = 100

# Expected payoff to the FIRST bird in each pairing
HH = (FOOD - INJURY_COST) / 2        # hawk v hawk: coin-flip fight          -> -25
HD = FOOD                            # hawk v dove: dove flees, hawk eats    ->  50
DH = 0                               # dove v hawk: runs away, costs nothing ->   0
DD = (FOOD - 2 * DISPLAY_COST) / 2   # dove v dove: both display, one eats   ->  15


# --------------------------------------------------------------------------
# Theory: exact expected payoffs, so the simulation can be checked
# --------------------------------------------------------------------------
class Theory:
    @staticmethod
    def payoff(p_self: float, p_other: float) -> float:
        """Expected points per conflict for a bird that plays hawk with
        probability p_self against one that plays hawk with p_other."""
        return (p_self * p_other * HH + p_self * (1 - p_other) * HD
                + (1 - p_self) * p_other * DH + (1 - p_self) * (1 - p_other) * DD)

    @staticmethod
    def hawk_payoff(p: float) -> float:
        return Theory.payoff(1.0, p)

    @staticmethod
    def dove_payoff(p: float) -> float:
        return Theory.payoff(0.0, p)

    @staticmethod
    def population_average(p: float) -> float:
        return Theory.payoff(p, p)

    @staticmethod
    def ess_hawk_fraction() -> float:
        """Hawk share at which hawks and doves score the same."""
        return (DD - HD) / (HH - HD - DH + DD)


def report_theory() -> None:
    p = Theory.ess_hawk_fraction()
    frac = Fraction(p).limit_denominator(100)
    hawks, doves = frac.numerator, frac.denominator - frac.numerator

    print("Average points per conflict for the ROW bird")
    print("              vs hawk   vs dove")
    print(f"  hawk       {HH:>7.1f}   {HD:>7.1f}")
    print(f"  dove       {DH:>7.1f}   {DD:>7.1f}\n")

    print(f"{'hawks':>7} {'hawk gets':>10} {'dove gets':>10} {'pop avg':>8}   what happens")
    for q in (0.0, 0.25, 0.5, p, 0.75, 1.0):
        h, d = Theory.hawk_payoff(q), Theory.dove_payoff(q)
        if abs(h - d) < 1e-9:
            verdict = "STABLE (ESS): neither spreads"
        elif h > d:
            verdict = "hawks spread"
        else:
            verdict = "doves spread"
        print(f"{q*100:>6.1f}% {h:>10.2f} {d:>10.2f} {Theory.population_average(q):>8.2f}   {verdict}")

    print(f"\nESS: {doves} doves for every {hawks} hawks  ({frac} hawks, "
          f"each bird averages {Theory.population_average(p):.2f} points/conflict)")


# --------------------------------------------------------------------------
# Birds and fights
# --------------------------------------------------------------------------
@dataclass
class Bird:
    p_hawk: float                # 0 = pure dove, 1 = pure hawk, between = mixed
    score: float = 0.0
    games: int = 0

    @classmethod
    def dove(cls) -> "Bird":
        return cls(0.0)

    @classmethod
    def hawk(cls) -> "Bird":
        return cls(1.0)

    @property
    def kind(self) -> str:
        return "dove" if self.p_hawk == 0 else "hawk" if self.p_hawk == 1 else "mixed"

    @property
    def mean_score(self) -> float:
        return self.score / self.games if self.games else 0.0

    def act(self) -> str:
        """Choose hawk or dove behaviour for this one encounter."""
        return "hawk" if random.random() < self.p_hawk else "dove"


class Confrontation:
    @staticmethod
    def resolve(a: str, b: str) -> tuple[float, float]:
        """Points for two birds that have chosen to act as `a` and `b`."""
        if a == "hawk" and b == "hawk":              # fight: winner eats, loser injured
            if random.random() < 0.5:
                return FOOD, -INJURY_COST
            return -INJURY_COST, FOOD
        if a == "hawk":                              # dove runs away at once
            return FOOD, 0
        if b == "hawk":
            return 0, FOOD
        win, lose = FOOD - DISPLAY_COST, -DISPLAY_COST   # both display, one backs down
        return (win, lose) if random.random() < 0.5 else (lose, win)


# --------------------------------------------------------------------------
# Population
# --------------------------------------------------------------------------
class Population:
    def __init__(self, birds: list[Bird], *, encounters: int = 30,
                 free_food_prob: float = 0.0, demographic: bool = False,
                 capacity: int | None = None, mutation_sd: float = 0.0,
                 pure_mutants: bool = False, baseline: float = 50.0):
        self.birds = birds
        self.encounters = encounters          # food finds per bird per generation
        self.free_food_prob = free_food_prob  # chance a find has no rival present
        self.demographic = demographic        # True: population size can shrink/grow
        self.capacity = capacity or len(birds)
        self.mutation_sd = mutation_sd        # evolves p_hawk if > 0
        self.pure_mutants = pure_mutants      # a lost pure type re-arises by mutation
        self.baseline = baseline
        self.generation = 0

    @classmethod
    def from_mix(cls, doves: int, hawks: int, **kw) -> "Population":
        return cls([Bird.dove() for _ in range(doves)] +
                   [Bird.hawk() for _ in range(hawks)], **kw)

    @classmethod
    def uniform(cls, size: int, p_hawk: float, **kw) -> "Population":
        return cls([Bird(p_hawk) for _ in range(size)], **kw)

    @property
    def size(self) -> int:
        return len(self.birds)

    # ---- one generation of food finding ---------------------------------
    def play_round(self) -> None:
        for b in self.birds:
            b.score, b.games = 0.0, 0
        n = self.size
        if n == 0:
            return
        for b in self.birds:                       # food nobody else contests
            for _ in range(self.encounters):
                if random.random() < self.free_food_prob:
                    b.score += FOOD
                    b.games += 1
        if n >= 2:                                 # contested food
            pairs = round(n * self.encounters * (1 - self.free_food_prob) / 2)
            for _ in range(pairs):
                x, y = random.sample(self.birds, 2)
                px, py = Confrontation.resolve(x.act(), y.act())
                x.score += px
                y.score += py
                x.games += 1
                y.games += 1

    # ---- statistics ------------------------------------------------------
    def stats(self) -> dict:
        def avg(pred):
            grp = [b for b in self.birds if pred(b)]
            games = sum(b.games for b in grp)
            return sum(b.score for b in grp) / games if games else None
        return {
            "size": self.size,
            "hawk_pct": 100 * sum(b.p_hawk for b in self.birds) / self.size,
            "avg": avg(lambda b: True) or 0.0,
            "dove_avg": avg(lambda b: b.p_hawk == 0),
            "hawk_avg": avg(lambda b: b.p_hawk == 1),
        }

    # ---- next generation -------------------------------------------------
    def _mutate(self, p: float) -> float:
        if self.mutation_sd <= 0:
            return p
        return min(1.0, max(0.0, p + random.gauss(0, self.mutation_sd)))

    def reproduce(self) -> None:
        if self.demographic:
            # 1 offspring on average, more if well fed, none if losing fights
            new: list[Bird] = []
            for b in self.birds:
                mean_kids = max(0.0, 1 + b.mean_score / FOOD)
                kids = int(mean_kids) + (random.random() < mean_kids - int(mean_kids))
                new += [Bird(self._mutate(b.p_hawk)) for _ in range(kids)]
            if len(new) > self.capacity:
                new = random.sample(new, self.capacity)
            if len(new) < 2:                       # a lone bird cannot carry on the species
                new = []
        else:
            # fixed size: strategies spread in proportion to their success
            weights = [max(0.01, self.baseline + b.mean_score) for b in self.birds]
            parents = random.choices(self.birds, weights=weights, k=self.size)
            new = [Bird(self._mutate(p.p_hawk)) for p in parents]

        if self.pure_mutants and len(new) >= 2:    # "a mutation arises"
            if not any(b.p_hawk == 1 for b in new):
                random.choice(new).p_hawk = 1.0
            if not any(b.p_hawk == 0 for b in new):
                random.choice(new).p_hawk = 0.0
        self.birds = new
        self.generation += 1


# --------------------------------------------------------------------------
# Running and reporting
# --------------------------------------------------------------------------
def _f(x, w=9):
    return f"{'-':>{w}}" if x is None else f"{x:>{w}.1f}"


def run(pop: Population, generations: int, every: int = 1) -> None:
    print(f"{'gen':>4} {'birds':>6} {'hawk%':>6} {'avg/conflict':>12} "
          f"{'dove avg':>9} {'hawk avg':>9}  hawk share")
    for g in range(generations):
        pop.play_round()
        s = pop.stats()
        if g % every == 0 or g == generations - 1:
            filled = round(s["hawk_pct"] / 100 * 30)
            bar = "H" * filled + "d" * (30 - filled)
            print(f"{g:>4} {s['size']:>6} {s['hawk_pct']:>5.1f}% {s['avg']:>12.1f} "
                  f"{_f(s['dove_avg'])} {_f(s['hawk_avg'])}  {bar}")
        pop.reproduce()
        if pop.size == 0:
            print(f"{g + 1:>4} {0:>6}   *** EXTINCT ***")
            return


def measure(pop: Population, rounds: int = 100) -> dict:
    """Average points per conflict without evolution (population held fixed)."""
    acc = {"all": [0.0, 0], "dove": [0.0, 0], "hawk": [0.0, 0]}
    for _ in range(rounds):
        pop.play_round()
        for b in pop.birds:
            keys = ["all"] + (["dove"] if b.p_hawk == 0 else ["hawk"] if b.p_hawk == 1 else [])
            for k in keys:
                acc[k][0] += b.score
                acc[k][1] += b.games
    return {k: (s / g if g else None) for k, (s, g) in acc.items()}


def title(text: str) -> None:
    print("\n" + "=" * 72 + f"\n{text}\n" + "=" * 72)


# --------------------------------------------------------------------------
# Scenarios
# --------------------------------------------------------------------------
def scenario_theory(a):
    title("THEORY - payoffs and the stable mix (ESS)")
    report_theory()


def scenario_doves(a):
    title("All doves = 'as near to Utopia as this model permits' ... then ONE hawk arises")
    print("Nobody gets hurt, everybody eats: 15 points per conflict. Watch the mutant.\n")
    run(Population.from_mix(a.size - 1, 1, pure_mutants=True), a.generations, a.every)


def scenario_hawks(a):
    title("All hawks = absolute disaster ... then ONE dove arises")
    print("Every conflict is a fight: -25 on average. A dove never fights and scores 0.\n")
    run(Population.from_mix(1, a.size - 1, pure_mutants=True), a.generations, a.every)


def scenario_extinction(a):
    title("An all-hawk population goes extinct - unless free food is plentiful")
    breakeven = -HH / (FOOD - HH)
    for f in (0.0, 0.5):
        print(f"\nFree food (no rival present) = {f:.0%} of finds "
              f"(break-even is {breakeven:.0%})")
        run(Population.from_mix(0, a.size, demographic=True, free_food_prob=f), 12, 1)


def scenario_welfare(a):
    title("The stable situation is not the best one")
    k = max(1, a.size // 12)
    ess = Population.from_mix(5 * k, 7 * k)
    r_dove = measure(Population.uniform(12 * k, 0.0))["all"]
    r_ess = measure(ess)["all"]
    r_hawk = measure(Population.uniform(12 * k, 1.0))["all"]
    print(f"{'society':<28} {'simulated':>10} {'theory':>8}")
    print(f"{'all doves':<28} {r_dove:>10.2f} {DD:>8.2f}")
    print(f"{'ESS (5 doves : 7 hawks)':<28} {r_ess:>10.2f} "
          f"{Theory.population_average(Theory.ess_hawk_fraction()):>8.2f}")
    print(f"{'all hawks':<28} {r_hawk:>10.2f} {HH:>8.2f}")
    print(f"\nEvolution settles on the ESS, which pays only {r_ess / r_dove:.0%} of the "
          f"all-dove society.\nStable is not necessarily best - individuals cannot "
          f"'agree' to stay doves.")


def scenario_mixed(a):
    title("5 doves : 7 hawks  ==  everyone plays dove 5/12 and hawk 7/12 of the time")
    k = max(1, a.size // 12)
    p = Theory.ess_hawk_fraction()
    pure = measure(Population.from_mix(5 * k, 7 * k), 150)
    mixed = measure(Population.uniform(12 * k, p), 150)
    print(f"{'population':<34} {'avg/conflict':>12}")
    print(f"{'pure mix: doves score':<34} {_f(pure['dove'], 12)}")
    print(f"{'pure mix: hawks score':<34} {_f(pure['hawk'], 12)}")
    print(f"{'pure mix: whole population':<34} {_f(pure['all'], 12)}")
    print(f"{'all mixed individuals (p=7/12)':<34} {_f(mixed['all'], 12)}")
    print(f"{'theory':<34} {Theory.population_average(p):>12.2f}")
    print("\nSame result either way: a population of pure types and a population of "
          "randomising individuals are indistinguishable.")


def scenario_evolve(a):
    title("Evolution finds the mixed strategy by itself (p_hawk mutates slightly)")
    p = Theory.ess_hawk_fraction()
    print(f"Everyone starts at p_hawk = 0.10. Target (ESS) = {p:.3f}\n")
    run(Population.uniform(a.size, 0.10, mutation_sd=0.03), a.generations * 3, max(1, a.every * 2))


SCENARIOS = {
    "theory": scenario_theory, "doves": scenario_doves, "hawks": scenario_hawks,
    "extinction": scenario_extinction, "welfare": scenario_welfare,
    "mixed": scenario_mixed, "evolve": scenario_evolve,
}


def main() -> None:
    ap = argparse.ArgumentParser(description="Hawk-Dove game from Deep Simplicity")
    ap.add_argument("scenario", nargs="?", default="all", choices=[*SCENARIOS, "all"])
    ap.add_argument("--size", type=int, default=240, help="population size")
    ap.add_argument("--generations", type=int, default=40)
    ap.add_argument("--every", type=int, default=4, help="print every Nth generation")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    random.seed(a.seed)
    for name in (SCENARIOS if a.scenario == "all" else [a.scenario]):
        SCENARIOS[name](a)


if __name__ == "__main__":
    main()
