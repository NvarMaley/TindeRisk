"""RiskMatch backlog DAG. Checklist remains the single source of completion status."""
from pathlib import Path
from graphlib import TopologicalSorter
import argparse
import csv
import io
import re

ROOT = Path(__file__).resolve().parents[1]
CHECKLIST = ROOT / "CHECKLIST_A_Z.md"
REGISTER = ROOT / "docs/TASK_DEPENDENCIES.csv"
PATTERN = re.compile(r"^- \[([ xX])\] \*\*([A-Z0-9.]+)\*\* — (.+)$", re.M)


def graph():
    rows = {key: (mark.lower() == "x", title) for mark, key, title in PATTERN.findall(CHECKLIST.read_text())}
    if len(rows) != len(PATTERN.findall(CHECKLIST.read_text())):
        raise ValueError("Duplicate ticket ID")
    deps = {}
    def put(key, *needs):
        if key in deps:
            raise ValueError(f"Duplicate dependency definition: {key}")
        deps[key] = set(needs)
    def chain(prefix, numbers, *needs):
        prev = list(needs)
        for n in numbers:
            key = f"{prefix}.{n:02}"
            put(key, *prev)
            prev = [key]
    def ch(n, numbers, *needs):
        chain(f"CH{n:02}", numbers, *needs)
    def many(prefix, count, step):
        return [f"{prefix}{i:02}.{step:02}" for i in range(1, count+1)]

    # Infrastructure and distinct model contracts; no financial model required yet.
    chain("INFRA", [1,2,3])
    chain("INFRA", [4,5,6], "INFRA.01")
    chain("INFRA", [7,8], "INFRA.06")
    ch(27, [1,2], "INFRA.01")
    put("SYS.01","CH27.02")
    put("SYS.02","SYS.01")
    ch(27,[9],"INFRA.02")
    ch(27,[11],"INFRA.08")
    put("G00","INFRA.03","INFRA.08","SYS.02","CH27.09","CH27.11")

    # Goals are specified before portfolio construction; their empirical validation is later.
    ch(1,[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15],"SYS.01")
    ch(12,[1,2,4,7],"CH01.05","SYS.01")
    ch(2,[1,2,5,6,7,8,9,3,4,10,11,12,13,14,21],"SYS.01")
    ch(2,[15,16,17,18,19,20],"CH02.14","CH01.07")
    put("G01","G00","CH01.15","CH12.07","CH02.21",*many("OBJ",11,1))

    # MVP universe first, extensions explicitly separated.
    ch(3,[1,2,3,4,9,10,11],"SYS.02")
    ch(4,[1,2,3],"CH03.02")
    # Metadata tooling can be verified with fixtures. Approval also requires the rights review.
    ch(4,[4,5,6,7,8],"CH04.02")
    put("CH04.09","CH04.03","CH04.08")
    # Private research normalization and synthetic leakage tests precede source approval.
    ch(5,[1,2,3,4,5,6,8,9,10,11,12],"CH04.08","CH03.04")
    ch(6,range(1,13),"CH05.11")
    put("UNIV.01","SYS.02","CH03.03","CH05.04")
    put("G02","G01","CH03.11","CH04.09","CH05.12","CH06.12","UNIV.01")

    # Basic statistics, forecast and risk. Advanced analyses may run only after applicable data.
    # Descriptive research and synthetic tests can precede actual data approval.
    ch(7,list(range(1,10)),"CH06.12")
    ch(8,[1,4,2],"CH05.09","CH07.06")
    ch(9,[1,2,8],"CH07.08")
    ch(11,[1,2,3,5,9,10],"CH07.08")
    ch(13,[1,5,6,2],"G02")
    ch(14,[1,2,3,4,5,6,7,8,10],"CH09.08","CH08.02","CH02.15","CH12.02")
    put("G03","G02","CH07.09","CH09.08","CH11.10","CH13.02","CH14.10")

    # Explicit baseline engine before full backtest or advanced economic model evaluation.
    ch(23,[1],"G02")
    chain("BT00",range(1,7),"G03","CH23.01")
    ch(13,[3,4,7,8,9],"BT00.03")
    put("G04","BT00.06","CH13.09")
    chain("MVP",range(1,5),"G04","G01")
    put("G05","MVP.04")
    ch(14,[9],"G04","CH14.08")

    # ETF-compatible risk and forecast refinements; factor-specific work later.
    ch(9,[3,4,5,7,9,10],"G04","CH09.08")
    ch(11,[4,6,7,8],"G04","CH11.03")
    ch(16,range(1,12),"G04","CH09.08")
    ch(17,range(1,11),"G04","CH11.03")
    ch(18,range(1,12),"G04","CH09.05")
    ch(15,[1,2,3,4,5,6],"G04","CH09.08")
    ch(19,[1,7,2],"G04","SYS.02")
    ch(20,[7,8,9,10],"G04","CH19.01")
    put("G06","G05","CH16.11","CH17.10","CH18.11","OPT08.10","OPT09.10","OPT12.10","STR01.10","STR12.10","STR16.10")

    # Extended data and ledger, including actual futures and bond accounting.
    # Catalog evidence can close before activation. Every consumer of the extension
    # retains the original model and data-quality gates.
    ch(3,[5,6,7,8],"CH03.04")
    ch(5,[7],"CH03.05","CH05.04")
    ch(21,range(1,13),"CH03.06","CH05.11","G06","CH04.09")
    ch(22,range(1,12),"CH03.07","CH05.11","G06","CH04.09")
    ch(23,[2,3,4,5,6,7,8,9,10,11,12,13,14],"G06","CH05.07","CH21.11","CH22.10","CH06.11")
    put("EXT.01","G06","CH03.08","CH05.07","CH21.11","CH22.10","CH04.09","UNIV.01")
    put("G07","CH23.14","CH21.12","CH22.11","EXT.01")

    # Advanced forecast, factor and strategy research.
    ch(10,range(1,12),"G07","CH05.07")
    ch(9,[6],"CH10.10","CH09.05")
    ch(8,[3],"CH10.04","CH15.06","CH08.02")
    ch(8,[5,6,7,8,9,10,11],"CH08.03","CH08.04","G07")
    ch(15,[7,8,9],"CH08.03","CH15.06","CH14.08")
    ch(19,[3,4,5,6,8,9,10],"CH19.02","CH10.08","CH08.08")
    ch(26,[3],"G07","CH08.04")  # regime estimator may precede dynamic policy
    ch(20,[1,2,3,4,5,6,11,12,13,14,15,16],"G07","CH19.08","CH20.10","CH26.03")
    ch(24,[1,2,3,4,5,6,7,8,9,10,11,12],"G07","CH09.10","CH11.07","CH26.03")
    ch(12,[3,5,6,8,9,10],"CH24.10","CH12.07")

    # Improvement first, then final matching, never promote unvalidated candidates.
    ch(25,range(15,22),"G07","CH08.11","CH15.09","CH20.16","CH24.12","CH12.10")
    put("IMP.01","CH25.21",*many("OPT",22,10),*many("STR",19,10),*many("FAC",13,10))
    put("IMP.02","IMP.01",*many("OBJ",11,10),*many("MET",23,5))
    ch(25,range(1,15),"IMP.02","G05")
    ch(25,range(22,29),"CH25.14","CH20.12","CH24.12")
    put("MATCH.01","CH25.28")
    put("G08","MATCH.01")
    ch(26,[1,2,7,5,6,8],"G08")
    ch(26,[4],"CH26.07",*many("DYN",10,8))
    ch(26,[9,10,11],"CH26.08","CH26.04",*many("DYN",10,10))
    ch(27,[7,8],"G00")
    ch(27,[3,4,5,6,12,13],"G08","CH27.08","CH26.11",*many("DYN",10,10))
    ch(27,[10],"G00","CH02.16")
    ch(27,[14,15],"CH27.13","CH27.10","CH02.20")
    put("G09","CH27.15","CH26.04")

    # Catalog tickets: .01 theory, .02 data, .03 prototype, .04/.05 tests,
    # .06 OOS, .07 sensitivity, .08 shared engine, .09 API/UI, .10 independent review.
    # Chapter-specific implementation prerequisites identify the actual inputs to each method.
    objective_impl = ["CH12.03","CH12.05","CH12.02","CH12.02","CH12.03","CH12.02","CH06.08","CH06.09","CH21.09","CH12.06","CH24.04"]
    optimizer_impl = ["CH13.02","CH13.05","CH14.02","CH14.05","CH14.03","CH14.04","CH15.08","CH16.03","CH16.06","CH16.07","CH16.08","CH17.02","CH17.03","CH17.04","CH17.05","CH18.02","CH18.03","CH18.04","CH18.05","CH18.06","CH17.06","CH17.07"]
    strategy_impl = ["CH19.02","CH19.03","CH20.01","CH20.02","CH20.03","CH20.04","CH20.12","CH20.05","CH19.05","CH19.04","CH20.06","CH20.07","CH20.08","CH20.09","CH19.06","CH20.10","CH20.11","CH20.13","CH20.14"]
    factor_impl = ["CH10.04","CH10.03","CH10.03","CH10.03","CH10.02","CH09.01","CH10.03","CH10.03","CH22.09","CH21.05","CH21.06","CH03.10","CH06.08"]
    dyn_impl = ["CH26.03","CH26.03","CH26.05","CH26.07","CH26.07","CH26.07","CH26.07","CH26.07","CH08.10","CH26.07"]
    for prefix, impl in [("OBJ",objective_impl),("OPT",optimizer_impl),("STR",strategy_impl),("FAC",factor_impl),("DYN",dyn_impl)]:
        for i, input_ticket in enumerate(impl,1):
            key=f"{prefix}{i:02}"
            theory = "CH12.01" if prefix=="OBJ" else "SYS.01"
            put(key+".01",theory)
            data_gate = "G02" if prefix in ("OBJ","OPT") else "G07"
            if prefix=="STR" and i in (1,12,13,14,16):
                data_gate="G02"
            if prefix=="DYN":
                data_gate="G08"
            data_needs = [data_gate]
            if prefix=="OBJ" and i==9:
                data_needs.append("CH21.04")
            if prefix=="OBJ" and i==11:
                data_needs.append("CH22.10")
            if prefix=="STR" and i in (4,5,6,8,11,19):
                data_needs.append("EXT.01")
            if prefix=="FAC":
                data_needs.append("EXT.01")
            put(key+".02",key+".01",*data_needs)
            put(key+".03",key+".02",input_ticket)
            chain(key,[4,5],key+".03")
            # ETF baseline validates eligible methods before extended ledger.
            eval_gate = "G04"
            if prefix=="DYN":
                eval_gate="G08"
            elif prefix=="FAC" or (prefix=="STR" and i not in (1,12,13,14,16)) or (prefix=="OBJ" and i in (9,11)):
                eval_gate="G07"
            put(key+".06",key+".05",eval_gate)
            chain(key,[7,8,9,10],key+".06")

    # Metrics have their own inputs; use reconciled ledger and relevant outputs.
    metric_inputs = ["BT00.03","BT00.03","CH06.11","CH06.11","CH07.02","BT00.03","CH11.05","CH11.05","CH17.04","CH11.05","CH11.02","CH11.03","CH10.04","CH17.06","CH17.07","CH14.08","CH16.01","CH22.06","CH23.04","CH03.10","CH18.10","CH10.09","CH12.06"]
    for i, input_ticket in enumerate(metric_inputs,1):
        key=f"MET{i:02}"
        put(key+".01","SYS.01")
        put(key+".02",key+".01",input_ticket,"G04")
        chain(key,[3,4,5],key+".02")

    # The final gate must cover every ticket, including evidence-only leaf nodes.
    referenced = set().union(*deps.values())
    deps["G09"].update(set(deps)-referenced-{"G09"})
    assert set(rows)==set(deps), f"Missing: {sorted(set(rows)-set(deps))}; extra: {sorted(set(deps)-set(rows))}"
    for key, need in deps.items():
        assert need <= rows.keys(), f"{key}: unknown dependencies {need-rows.keys()}"
        assert key not in need
    sorter=TopologicalSorter({k: sorted(v) for k,v in deps.items()})
    order=list(sorter.static_order())
    assert len(order)==len(rows)
    predecessors=set()
    pending=list(deps["G09"])
    while pending:
        item=pending.pop()
        if item not in predecessors:
            predecessors.add(item)
            pending.extend(deps[item])
    assert predecessors == set(rows)-{"G09"}, "Final gate lacks ticket coverage"
    def ancestors(ticket):
        seen=set()
        pending=list(deps[ticket])
        while pending:
            current=pending.pop()
            if current not in seen:
                seen.add(current)
                pending.extend(deps[current])
        return seen
    # Guard critical architecture boundaries against later checklist edits.
    assert set(many("OBJ",11,1)) <= ancestors("G01")
    assert "G01" in ancestors("G03")
    assert "UNIV.01" in ancestors("G02")
    assert "CH04.09" in ancestors("G02")
    assert "UNIV.01" in ancestors("MATCH.01")
    assert "BT00.06" in ancestors("G06")
    assert "G04" in ancestors("G05")
    assert "EXT.01" in ancestors("STR06.06")
    assert "EXT.01" in ancestors("FAC09.06")
    assert "IMP.02" in ancestors("MATCH.01")
    assert "MATCH.01" in ancestors("G09")
    assert set(many("DYN",10,10)) <= ancestors("G09")
    return rows,deps,order


def render(rows,deps,order):
    # Status lives only in the checklist, so checking a box never requires regeneration.
    out=io.StringIO()
    writer=csv.writer(out,lineterminator="\n")
    writer.writerow(["topological_order","ticket","direct_prerequisites","description"])
    for i,key in enumerate(order,1):
        writer.writerow([i,key,"; ".join(sorted(deps[key])),rows[key][1]])
    return out.getvalue()


def main():
    parser=argparse.ArgumentParser()
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build",action="store_true")
    mode.add_argument("--check",action="store_true")
    mode.add_argument("--ready",action="store_true")
    mode.add_argument("--task")
    parser.add_argument("--limit",type=int,default=25)
    args=parser.parse_args()
    rows,deps,order=graph()
    if args.build:
        REGISTER.write_text(render(rows,deps,order))
    elif args.check:
        assert REGISTER.read_text()==render(rows,deps,order), "Outdated registry: run --build"
        # Marking a dependent done before its prerequisites is invalid.
        premature=[key for key in order if rows[key][0] and any(not rows[p][0] for p in deps[key])]
        assert not premature, f"Tickets checked before prerequisites: {premature}"
        print(f"Valid DAG: {len(rows)} tickets, {sum(map(len,deps.values()))} direct dependencies, no cycles.")
    elif args.ready:
        ready=[k for k in order if not rows[k][0] and all(rows[p][0] for p in deps[k])]
        print(f"{len(ready)} ready ticket(s); {sum(v[0] for v in rows.values())}/{len(rows)} completed.")
        for key in ready[:args.limit]:
            print(f"{key} — {rows[key][1]}")
    else:
        key=args.task.upper()
        if key not in rows:
            parser.error(f"Unknown ticket: {key}")
        print(f"{key} — {rows[key][1]}")
        for p in sorted(deps[key]):
            print(f"  [{'x' if rows[p][0] else ' '}] {p} — {rows[p][1]}")
        if not deps[key]:
            print("  No prerequisites.")

if __name__=="__main__":
    main()
