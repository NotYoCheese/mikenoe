---
layout: post
title: Breaking Through the Plateau with Focal Loss
date: 2025-12-05
categories: ["Machine Learning", "Deep Learning", "MLOps", "Data Science"]
description: How systematic grid search testing with focal loss broke through a 41% F1 plateau, achieving 21% improvement on a 698-category multi-label classifier. A methodical approach to production ML optimization.
---

After weeks of training a ML model, I hit a wall at 41% F1 score.

I tried lots of tweaks. Added more training data for weak categories. Tuned hyperparameters. Adjusted class weights from 2.0 to 3.0 to 5.0. Nothing worked.

Then I ran a systematic grid search on AWS, and found a major improvement.

## The Problem

I'm building a multi-label classifier for 698 IAB content categories. The class imbalance is extreme—some categories have 1,000+ training examples, others have just 5-10.

The model kept optimizing for the common categories and ignoring the rare ones. I'd improved from a baseline F1 of 0.22 to 0.41. But then I plateaued. Hard.

## The Hypothesis

Class weights help, but they plateau around cap 5.0. Why? Because you're still optimizing the same loss function—just with different weights.

Focal loss is different. Instead of up-weighting rare categories, it down-weights easy examples. In other words: "Stop spending so much time on things you already know."

## The Method

I spun up an AWS EC2 instance (g4dn.2xlarge, Tesla T4 GPU) and ran a systematic grid search: 3 class weight caps (6.0, 7.0, 8.0) × 3 focal loss configurations (none, gamma=2.0, gamma=3.0) = 6 total model variants, ~30 minutes training each.

No guessing. No random tweaking. Just methodical testing.

## The Results

| Configuration | F1 Score | Improvement |
|--------------|----------|-------------|
| ⭐ cap_7.0_focal_g3 | 0.4973 | +21.0% |
| cap_8.0_focal_g2 | 0.4839 | +17.7% |
| cap_7.0_focal_g2 | 0.4727 | +15.0% |
| cap_7.0_no_focal | 0.4107 | -0.1% |
| cap_6.0_no_focal | 0.4033 | -1.9% |
| cap_8.0_no_focal | 0.3759 | -8.6% |

The winner: Class weight cap 7.0 + focal loss with gamma 3.0. **21% improvement** over the previous best model.

## The Insight

Class weights alone hit diminishing returns because you're still optimizing for easy examples—they're just weighted differently.

Focal loss fundamentally changes what the model focuses on during training. It says: "This common category is easy—reduce the loss signal. This rare category is hard—amplify it."

The breakthrough came from combining both approaches:
- **Class weights**: Compensate for frequency imbalance
- **Focal loss**: Focus learning on hard examples

Together, they broke through the plateau.

## The Lesson

When you hit a plateau, systematic testing beats intuition.

I could have kept tweaking parameters randomly. Instead, I:
1. Formed a hypothesis about why I was stuck
2. Designed a grid search to test it
3. Let the data show me what worked

Three hours on AWS. Six training runs. One breakthrough.

This is what production ML actually looks like—not magic, just methodical problem-solving.

Of course, 50% F1 still wasn't good enough. The next breakthrough? Even bigger. More on that soon.

## Further Reading

If you're interested in learning more about focal loss:

- **[Focal Loss for Dense Object Detection](https://arxiv.org/abs/1708.02002)** (Lin et al., 2017) - The seminal paper that introduced focal loss, won Best Student Paper Award at ICCV 2017

- **[Implementing Focal Loss in PyTorch for Class Imbalance](https://medium.com/data-scientists-diary/implementing-focal-loss-in-pytorch-for-class-imbalance-24d8aa3b59d9)** - Practical implementation guide with code examples and hyperparameter tuning tips

- **[A Loss Function Suitable for Class Imbalanced Data: Focal Loss](https://towardsdatascience.com/a-loss-function-suitable-for-class-imbalanced-data-focal-loss-af1702d75d75/)** - Clear conceptual explanation with visual examples and real-world use cases

**Have you hit similar plateaus in model training? What worked for you?**

#MachineLearning #DataScience #AI #MLOps #DeepLearning
