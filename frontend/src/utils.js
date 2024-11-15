export function waitTimeMinutesString(timestamp) {
  const minutes = Math.floor((Date.now() / 1000 - timestamp) / 60);
  return minutes < 1 ? "< 1" : minutes.toString();
}

export function ordinalString(number) {
  const s = number.toString();
  let suffix;
  if (["11", "12", "13"].includes(s.slice(-2))) {
    suffix = "th";
  } else {
    switch (s.slice(-1)) {
      case "1":
        suffix = "st";
        break;
      case "2":
        suffix = "nd";
        break;
      case "3":
        suffix = "rd";
        break;
      default:
        suffix = "th";
        break;
    }
  }

  return `${s}${suffix}`;
}
