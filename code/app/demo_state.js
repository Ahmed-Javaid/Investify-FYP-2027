/* Pure request ownership and verification freshness. No model or network work. */
(function (root) {
  'use strict';
  root.createInvestifyVerificationState = function () {
    let generation = 0;
    return {
      invalidate() { generation += 1; },
      begin(input) { return { generation: ++generation, identity: JSON.stringify(input) }; },
      matches(ticket, input) { return ticket.generation === generation && ticket.identity === JSON.stringify(input); }
    };
  };
  root.createInvestifyRequestState = function () {
    let generation = 0;
    return {
      invalidate() { generation += 1; },
      begin() { return ++generation; },
      isCurrent(ticket) { return ticket === generation; }
    };
  };
})(globalThis);
