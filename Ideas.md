I have have a revisions.md (rev#.md) file in my project and have Claud-Dev either create or modify the revisions.md file acordingly.. rev1.md, rev2.md. and maybe a design.md or process.md file with pertinent information. Then in my prompt I will do something like this.

Design.md contains The purpose of the project what needs to be acomplished, any design related information, psudo-code and other related project information.

Using the @design.md and @rev1.md I would like you to continue working on blah blah when your complete create a rev2.md file with updated status of the project and next steps. Then in the next prompt to continue I will do the same but then reference rev2.md instead of rev1.md.

At times I will do something like this. Using @design.md, @rev1.md @rev2.md @rev3.md ... make sure that we have implemented such and such. Provide a new design1.md document so that we can continue going forward.

I keep my revisions and then if I need to, or it gets lost I can always use the prompt to tell it to go though a certain revision if needed.
It seems to be working fairly well. Where Claud-Dev can create whatever file I tell it to it makes it nice to be able to handle revisions, document updates etc.

My actual last prompt I was using:
Using the existing solution code, @Design2.md, @Rev17.md as well as the code snippets.  evaluate the solution, the  iterations and existing code base and combine them for the ultimate solution.  When using the existing codebase make sure that the solution uses as much of the existing code as possible in implementing this "feature" implementation.  First act as a code reviewer and find any issues or items that have been missed. Provide a comprehensive list of items that still need to be implemented. Provide any pseudocode or examples that the coder could use. 

Then act as an expert thorough senior coder and use the suggestions from the reviewer to address each item given by the reviewer.  Make code changes and provide the new ultimate solution. For ANY pseudocode that is used within the examples implement the pseudocode.  Provide the complete code from the codebase with the added changes so that I can now add files and changes to the existing solution.  

Using the new code from the Coder and the suggestions from the Reviewer provide an Update that can be added to the design document.

Sometimes I will get 10-20 revisions deep before I will let Claud-Dev make any actual code changes. all of the code changes will be in the rev#.md file(s)
***If any of you have better suggestions or a better modified version of this please share....