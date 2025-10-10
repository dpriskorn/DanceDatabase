# Dance Database

This is an attempt to create a data backbone 
for the Scandinavian social dance community 
which the author is happy to be a part of.

## Vision
One place where event organizers publish their events which can then be fanned out to mulitple applications and used in LLMs by everyone.

It's similar to what [musicbrainz](https://musicbrainz.org/) is for CDs or [Wikidata](https://www.wikidata.org/) is for notable world events.

## Use cases
Questions the collected data should support answering
* When does the event start and end
* Which other events collide
* How far from me is the event
* What is the schedule?
* When does registration open?
* Are there tiered prices and what are they?
* Who is the organizer?
* Where can I sign up?

Questions it should not answer:
* How do I get there? (can be solved via GraphHopper or similar services)
* What did this organizer organize before? (can be solved using SPARQL)
* Are there lodging nearby (Openstreetmap or similar can be used)
* How can I contact the organizer (we only provide an organizer website link for now)

### Excluded data
We decided not to include the following based on the user cases above
email: str = ""
phone: str = ""

## Goals
1) create a versioned open specification for dance event data
2) provide an API that anyone can use to build end user applications upon
3) provide a database with [FAIR](https://www.go-fair.org/fair-principles/) event data
5) increase findability for dance events
6) non-profitability of the project

## What Dance Database is not
* a website directly used by dancers to find dances (others do that better).
* an image hosting service.

## What Dance Database should provide
1) A UI that make it easy for event organizers to add events 
2) A stable service over time run by donations/contributions for the good of everyone in the community

## Nice to have
2) Something that runs in Kubernetes and is reliable and scalable
3) FAIR data with GUPRIs
4) Graph data and statistics

# License
All code is under GPLv3 and all data in data/ is licensed CC0.