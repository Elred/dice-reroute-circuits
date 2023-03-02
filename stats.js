/**
 * Returns a "face" entry.
 * @param {*} values - Symbols of the face.
 * @param {*} count - Count of the face.
 * @returns {values: array, count: number}
 */
function makeFace (values, count = 1) {
    return {values: Array.isArray(values) ? values : [values], count};
}
/**
 * Cumulates the similar faces and adds up their counts.
 * @param {*} faces 
 * @param {*} options
 * @returns {{values: array, count: number}[]}
 */
function cumulate (faces, options = {ordered: false}) {
    const cumulated = {};
    for (const face of faces) {
        const key = (options?.ordered ? face.values : face.values.sort()).join('');
        cumulated[key] = makeFace(face.values, face.count + (cumulated[key]?.count ?? 0));
    }
    return Object.values(cumulated);
}
/**
 * Returns a "dice" structure (basically an array of "faces").
 * @param {*} valuesByFaces - raw list of the values on each face.
 * @returns {{values: array, count: number}[]}
 */
function makeDice (valuesByFaces) {
    return cumulate(valuesByFaces.map(v => makeFace(v)));
}
/**
 * Generates a list of values/count by combining each line of a with every line of b.
 * @param {{values: array, count: number}[]} a 
 * @param {{values: array, count: number}[]} b 
 * @param {*} options 
 * @returns {{values: array, count: number}[]}
 */
function combine (a, b, options = {ordered: false}) {
    const combinations = {};
    for (const aVal of a) {
        for (const bVal of b) {
            const newVals = [...aVal.values, ...bVal.values];
            const newCount = aVal.count * bVal.count;
            const key = (options?.ordered ? newVals : newVals.sort()).join('');        
            combinations[key] = makeFace(newVals, newCount + (combinations[key]?.count ?? 0));
        }
    }
    return Object.values(combinations);
}
/**
 * Applies "combine" with n times the "dice" values.
 * @param {{values: array, count: number}[]} dice
 * @param {number} n
 * @param {*} options 
 * @returns {{values: array, count: number}[]}
 */
function combineN (dice, n, options = {ordered: false}) {
    if (n <= 0) {
        return [];
    } else if (n === 1) {
        return dice;
    } else if (n === 2) {
        return combine(dice, dice, options);
    } else {
        return combine(dice, combineN(dice, n - 1, options), options);
    }
}
/**
 * Returns the total number of scenarios (even similar ones) for the given combination list (sum of all counts).
 * @param {{values: array, count: number}[]} combinations 
 * @returns {number}
 */
function totalCount (combinations) {
    return combinations.reduce((sum, c) => sum + c.count, 0);
}
/**
 * Returns the probability of getting every possible outcome from the given callback. The callback is given the value of a face (symbol(s)) and must return a number.
 * @param {{values: array, count: number}[]} combinations 
 * @param {function} cb 
 * @returns {array<{nb: number, proba: number}>}
 */
function chancesOfCb (combinations, cb) {
    const total = totalCount(combinations);
    const results = {};
    for (const combo of combinations) {
        const valueCount = cb(combo.values);
        results[valueCount] = combo.count + (results[valueCount] ?? 0);
    }
    return Object.entries(results).map(([nb, count]) => ({nb: Number.parseInt(nb), proba: count/total}));
}
/**
 * Shortcut to get the chances of having 0..n times the given value.
 * @param {{values: array, count: number}[]} combinations 
 * @param {*} value 
 * @returns {{array<{nb: number, proba: number}>}
 */
function chancesOf (combinations, value) {
    return chancesOfCb(combinations, values => values.filter(v => v === value).length);
}
/**
 * Returns the chances of having at least "min" times the given value.
 * @param {{values: array, count: number}[]} combinations 
 * @param {*} value 
 * @param {number} min 
 * @returns {number}
 */
function chancesOfAtLeast (combinations, value, min) {
    const chances = chancesOf(combinations, value);
    return chances.reduce((sum, current) => sum + (current.nb >= min ? current.proba : 0), 0);
}

const redDice = makeDice(['blank', 'blank', 'hit', 'hit', 'crit', 'crit', 'acc', 'hit+hit']);

const combined = combineN(redDice, 15);
console.log(combined);

const chancesOfAcc = chancesOf(combined, 'acc');
console.log(chancesOfAcc);

const chancesOfCrit = chancesOfAtLeast(combined, 'crit', 1);
console.log(chancesOfCrit);

const dmgTable = {'hit': 1, 'crit': 1, 'hit+hit': 2};
const chancesOfDmg = chancesOfCb(combined, values => values.reduce((dmg, current) => dmg + (dmgTable[current] ?? 0), 0));
console.log(chancesOfDmg);